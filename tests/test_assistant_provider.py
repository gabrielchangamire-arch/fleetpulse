from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError

from fleetpulse.assistant.app import create_app
from fleetpulse.assistant.config import AssistantSettings
from fleetpulse.assistant.models import (
    AnalysisRequest,
    EvidenceInput,
    EvidenceItem,
    ProviderAnalysis,
)
from fleetpulse.assistant.providers import OpenAIResponsesProvider, ProviderFailure
from fleetpulse.assistant.service import AssistantService
from fleetpulse_project.incident_eval import FixtureProvider, evaluate


def output() -> dict[str, Any]:
    return {
        "summary": "Uncited diagnosis that must not reach users",
        "claims": [
            {
                "text": "A worker stopped.",
                "citations": ["E1"],
                "evidence_excerpts": [{"evidence_id": "E1", "excerpt": "worker stopped"}],
            }
        ],
        "proposed_remediations": [],
        "abstained": False,
        "abstention_reason": None,
    }


def envelope() -> dict[str, Any]:
    return {
        "status": "completed",
        "output": [
            {"type": "reasoning"},
            {"type": "message", "content": [{"type": "output_text", "text": json.dumps(output())}]},
        ],
        "usage": {"input_tokens": 100, "output_tokens": 50},
    }


def provider(handler: Any, retries: int = 0) -> OpenAIResponsesProvider:
    return OpenAIResponsesProvider(
        AssistantSettings(
            provider="openai",
            api_key=SecretStr("test-only-placeholder"),
            max_retries=retries,
            input_cost_per_million=1,
            output_cost_per_million=2,
        ),
        transport=httpx.MockTransport(handler),
    )


async def call(adapter: OpenAIResponsesProvider) -> ProviderAnalysis:
    return await adapter.analyze(
        "What happened?", [EvidenceItem(id="E1", source="log", content="worker stopped")]
    )


async def test_success_http_contract() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://api.openai.com/v1/responses"
        assert request.headers["Authorization"] == "Bearer test-only-placeholder"
        assert request.headers["X-Client-Request-Id"]
        payload = json.loads(request.content)
        assert payload["tools"] == [] and payload["store"] is False
        assert payload["max_output_tokens"] == 2000
        schema = payload["text"]["format"]["schema"]
        assert set(schema["required"]) == set(schema["properties"])
        assert "_metrics" not in schema["properties"]
        assert schema["additionalProperties"] is False
        return httpx.Response(200, json=envelope(), headers={"x-request-id": "req_123"})

    result = await call(provider(handler))
    assert result._metrics.request_id == "req_123"
    assert result._metrics.attempts == 1
    assert result._metrics.estimated_cost_usd == 0.0002
    assert result._metrics.latency_ms >= 0


@pytest.mark.parametrize(
    "bad,code",
    [
        ({"status": "incomplete", "output": []}, "incomplete"),
        (
            {
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "refusal", "refusal": "sensitive provider text"}],
                    }
                ],
            },
            "refusal",
        ),
        ({"status": "completed", "output": []}, "malformed_output"),
        (
            {
                "status": "completed",
                "output": [
                    {"type": "message", "content": [{"type": "output_text", "text": "not json"}]}
                ],
            },
            "malformed_output",
        ),
        ([], "malformed_output"),
    ],
)
async def test_bad_responses_fail_once_without_body_leak(bad: Any, code: str) -> None:
    with pytest.raises(ProviderFailure) as caught:
        await call(provider(lambda r: httpx.Response(200, json=bad), retries=2))
    assert str(caught.value) == code
    assert caught.value.metrics.attempts == 1


@pytest.mark.parametrize("status", [408, 409, 429, 500, 503])
async def test_retryable_then_success(status: int) -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return (
            httpx.Response(status, json={})
            if attempts == 1
            else httpx.Response(200, json=envelope())
        )

    result = await call(provider(handler, retries=1))
    assert attempts == result._metrics.attempts == 2


@pytest.mark.parametrize("status", [400, 401, 403, 422])
async def test_permanent_failure_is_not_retried(status: int) -> None:
    with pytest.raises(ProviderFailure) as caught:
        await call(provider(lambda r: httpx.Response(status, text="secret body"), retries=2))
    assert caught.value.metrics.attempts == 1
    assert "secret" not in str(caught.value)


@pytest.mark.parametrize("kind", ["timeout", "network", "rate_limit", "server"])
async def test_exhausted_retries(kind: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if kind == "timeout":
            raise httpx.ReadTimeout("secret body", request=request)
        if kind == "network":
            raise httpx.ConnectError("secret body", request=request)
        return httpx.Response(429 if kind == "rate_limit" else 500)

    with pytest.raises(ProviderFailure) as caught:
        await call(provider(handler, retries=2))
    assert caught.value.metrics.attempts == 3
    assert "secret" not in str(caught.value)


async def test_quota_and_long_retry_after_do_not_retry() -> None:
    for response in [
        httpx.Response(429, json={"error": {"code": "insufficient_quota"}}),
        httpx.Response(429, headers={"retry-after": "100"}),
    ]:
        with pytest.raises(ProviderFailure) as caught:
            await call(provider(lambda r, response=response: response, retries=3))
        assert caught.value.metrics.attempts == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("max_retries", -1),
        ("max_retries", 99),
        ("request_timeout_seconds", 0),
        ("max_output_tokens", 100000),
    ],
)
def test_configuration_is_bounded(field: str, value: int) -> None:
    with pytest.raises(ValidationError):
        AssistantSettings.model_validate({field: value})


@pytest.mark.parametrize(
    "excerpt,citation,abstained",
    [
        ("worker stopped", "E1", False),
        ("worker crashed", "E1", True),
        ("worker stopped", "E2", True),
    ],
)
async def test_excerpt_match_boundary(excerpt: str, citation: str, abstained: bool) -> None:
    result = output()
    result["claims"][0]["evidence_excerpts"][0].update(excerpt=excerpt, evidence_id=citation)
    response = await AssistantService(FixtureProvider(result)).analyze(
        AnalysisRequest(
            question="What happened?",
            evidence=[EvidenceInput(source="log", content="worker stopped")],
        )
    )
    assert response.abstained is abstained
    assert "Uncited" not in response.summary


async def test_real_but_irrelevant_excerpt_is_not_semantic_validation() -> None:
    result = output()
    result["claims"][0]["text"] = "Database corruption caused the outage."
    response = await AssistantService(FixtureProvider(result)).analyze(
        AnalysisRequest(
            question="What happened?",
            evidence=[EvidenceInput(source="log", content="worker stopped")],
        )
    )
    assert not response.abstained
    assert response.grounding == "excerpt-match-only"


async def test_versioned_dataset_is_disjoint_and_exposes_semantic_failures() -> None:
    root = Path("evaluations/incidents-v1")
    ids: set[str] = set()
    for split in ["development", "held-out"]:
        data = json.loads((root / f"{split}.json").read_text())
        assert len(data["cases"]) >= 15
        new_ids = {c["id"] for c in data["cases"]}
        assert not ids & new_ids
        ids |= new_ids
        report = await evaluate(root / f"{split}.json")
        assert all(row["boundary_pass"] for row in report["results"])
        assert report["metrics"]["redaction_failures"] == 0
        assert report["metrics"]["claim_support"]["rate"] < 1
    assert len(ids) >= 30


def test_demo_and_cross_origin_guard() -> None:
    with TestClient(create_app(AssistantSettings())) as client:
        assert "Claims & citations" in client.get("/").text
        cases = client.get("/demo/incidents").json()
        assert len(cases) == 16
        assert "synthetic-db-secret" not in json.dumps(cases)
        assert "labels" not in cases[0]
        request = {k: cases[0][k] for k in ("question", "evidence")}
        assert client.post("/v1/analysis", json=request).status_code == 200
        assert (
            client.post(
                "/v1/analysis", json=request, headers={"origin": "https://elsewhere.invalid"}
            ).status_code
            == 403
        )


@pytest.mark.parametrize(
    "value",
    [
        'password="synthetic secret with spaces"',
        "token='synthetic secret with spaces'",
        '"password": "synthetic secret with spaces"',
    ],
)
def test_redaction_of_quoted_values(value: str) -> None:
    from fleetpulse.assistant.redaction import SecretRedactor

    assert "synthetic secret" not in SecretRedactor().redact(value).text
