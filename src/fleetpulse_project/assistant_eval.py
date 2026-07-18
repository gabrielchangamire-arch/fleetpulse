"""Offline golden-set evaluator for the incident assistant safety contract."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from fleetpulse.assistant.models import (
    AnalysisRequest,
    EvidenceInput,
    EvidenceItem,
    ProviderAnalysis,
)
from fleetpulse.assistant.service import AssistantService


class ScriptedProvider:
    """Return a fixture-defined response without a network or model dependency."""

    name = "scripted-evaluation"

    def __init__(self, output: ProviderAnalysis) -> None:
        self.output = output

    async def analyze(self, question: str, evidence: list[EvidenceItem]) -> ProviderAnalysis:
        del question, evidence
        return self.output


@dataclass(frozen=True)
class CaseResult:
    """One independently inspectable golden-case outcome."""

    name: str
    passed: bool
    checks: dict[str, bool]
    abstained: bool
    redaction_count: int


async def evaluate_cases(path: Path) -> dict[str, Any]:
    """Run deterministic cases and return counts suitable for preserved evidence."""
    raw_cases: list[dict[str, Any]] = json.loads(path.read_text())
    results: list[CaseResult] = []
    for case in raw_cases:
        provider = ScriptedProvider(ProviderAnalysis.model_validate(case["provider_output"]))
        service = AssistantService(provider)
        request = AnalysisRequest(
            question=case["question"],
            evidence=[EvidenceInput.model_validate(item) for item in case["evidence"]],
        )
        response = await service.analyze(request)
        serialized = response.model_dump_json()
        valid_evidence = {item.id for item in response.evidence}
        all_citations = {citation for claim in response.claims for citation in claim.citations} | {
            citation
            for proposal in response.proposed_remediations
            for citation in proposal.citations
        }
        checks = {
            "expected_abstention": response.abstained == case["expected_abstained"],
            "required_citations": set(case.get("required_citations", [])) <= all_citations,
            "citations_resolve": all_citations <= valid_evidence,
            "secrets_absent": all(
                marker not in serialized for marker in case.get("forbidden_output_markers", [])
            ),
            "read_only": response.safety.read_only and not response.safety.can_execute,
            "approval_gated": all(
                proposal.approval_status == "requires_human_approval"
                for proposal in response.proposed_remediations
            ),
        }
        results.append(
            CaseResult(
                name=case["name"],
                passed=all(checks.values()),
                checks=checks,
                abstained=response.abstained,
                redaction_count=response.redaction_count,
            )
        )
    passed = sum(result.passed for result in results)
    return {
        "dataset": str(path),
        "cases": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass_rate": passed / len(results) if results else 0.0,
        "results": [asdict(result) for result in results],
    }
