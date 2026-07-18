"""Safety and API tests for the optional incident assistant."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from fleetpulse.assistant.app import create_app
from fleetpulse.assistant.config import AssistantSettings
from fleetpulse.assistant.models import (
    AnalysisRequest,
    Claim,
    EvidenceInput,
    EvidenceItem,
    ProviderAnalysis,
    ProviderRemediation,
    ReviewRequest,
)
from fleetpulse.assistant.redaction import REDACTED, SecretRedactor
from fleetpulse.assistant.service import AssistantService, DuplicateReviewError
from fleetpulse_project.assistant_eval import evaluate_cases


class CapturingProvider:
    name = "capture"

    def __init__(self, output: ProviderAnalysis) -> None:
        self.output = output
        self.seen_evidence: list[EvidenceItem] = []

    async def analyze(self, question: str, evidence: list[EvidenceItem]) -> ProviderAnalysis:
        self.seen_evidence = evidence
        assert "question-evaluation-value" not in question
        return self.output


def supported_output(citation: str = "E1") -> ProviderAnalysis:
    return ProviderAnalysis(
        summary="Supported summary.",
        claims=[Claim(text="A supported claim.", citations=[citation])],
        proposed_remediations=[
            ProviderRemediation(
                action="Inspect the component.",
                rationale="The evidence names it.",
                citations=[citation],
            )
        ],
        abstained=False,
        abstention_reason=None,
    )


def test_redactor_handles_headers_assignments_urls_and_keys() -> None:
    private_key = "-----BEGIN PRIVATE KEY-----\nvalue\n-----END PRIVATE KEY-----"
    source = (
        "Authorization: Bearer header-evaluation-value "
        "password=assignment-evaluation-value "
        "postgresql://user:url-evaluation-value@db/fleet " + private_key
    )
    result = SecretRedactor().redact(source)
    assert result.count == 4
    assert result.text.count(REDACTED) == 4
    for marker in (
        "header-evaluation-value",
        "assignment-evaluation-value",
        "url-evaluation-value",
        "\nvalue\n",
    ):
        assert marker not in result.text


@pytest.mark.asyncio
async def test_input_is_redacted_before_provider_and_proposals_require_approval() -> None:
    provider = CapturingProvider(supported_output())
    service = AssistantService(provider)
    response = await service.analyze(
        AnalysisRequest(
            question="token=question-evaluation-value what happened?",
            evidence=[
                EvidenceInput(
                    source="log",
                    content="password=evidence-evaluation-value connection failed",
                )
            ],
        )
    )
    serialized_provider_input = repr(provider.seen_evidence)
    assert "evidence-evaluation-value" not in serialized_provider_input
    assert response.redaction_count == 2
    assert response.proposed_remediations[0].approval_status == "requires_human_approval"
    assert response.safety.read_only is True
    assert response.safety.can_execute is False


@pytest.mark.asyncio
async def test_unknown_citation_forces_safe_abstention() -> None:
    service = AssistantService(CapturingProvider(supported_output("E404")))
    response = await service.analyze(
        AnalysisRequest(
            question="What happened?",
            evidence=[EvidenceInput(source="log", content="worker stopped")],
        )
    )
    assert response.abstained is True
    assert response.claims == []
    assert response.proposed_remediations == []
    assert "E404" in (response.abstention_reason or "")


@pytest.mark.asyncio
async def test_provider_output_is_redacted_before_return() -> None:
    output = supported_output()
    output.summary = "token=provider-evaluation-value"
    service = AssistantService(CapturingProvider(output))
    response = await service.analyze(
        AnalysisRequest(
            question="What happened?",
            evidence=[EvidenceInput(source="log", content="worker stopped")],
        )
    )
    assert "provider-evaluation-value" not in response.model_dump_json()
    assert response.summary == f"token={REDACTED}"
    assert response.redaction_count == 1


@pytest.mark.asyncio
async def test_review_requires_generated_proposal_and_never_executes() -> None:
    service = AssistantService(CapturingProvider(supported_output()))
    analysis = await service.analyze(
        AnalysisRequest(
            question="What happened?",
            evidence=[EvidenceInput(source="log", content="worker stopped")],
        )
    )
    receipt = await service.review(
        ReviewRequest(
            analysis_id=analysis.analysis_id,
            proposal_id=analysis.proposed_remediations[0].id,
            reviewer="on-call@example.invalid",
            decision="approved",
            rationale="Reviewed against the cited log.",
        )
    )
    assert receipt.execution_available is False
    with pytest.raises(DuplicateReviewError):
        await service.review(
            ReviewRequest(
                analysis_id=analysis.analysis_id,
                proposal_id=analysis.proposed_remediations[0].id,
                reviewer="on-call@example.invalid",
                decision="approved",
                rationale="Duplicate decision.",
            )
        )


def test_http_surface_has_no_execution_route() -> None:
    app = create_app(AssistantSettings(provider="offline"))
    paths = {route.path for route in app.routes if isinstance(route, APIRoute)}
    assert "/v1/analysis" in paths
    assert "/v1/reviews" in paths
    assert not any("execute" in path or "remediate" in path for path in paths)
    with TestClient(app) as client:
        response = client.get("/readyz")
        assert response.status_code == 200
        assert response.json()["authority"] == "read-only"


@pytest.mark.asyncio
async def test_golden_set_passes() -> None:
    result = await evaluate_cases(Path("evaluations/assistant_golden.json"))
    assert result["cases"] == 5
    assert result["pass_rate"] == 1.0
