"""Versioned synthetic evaluation; fixture contract checks are not live-model accuracy."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any

from fleetpulse.assistant.config import AssistantSettings
from fleetpulse.assistant.models import AnalysisRequest, EvidenceItem, ProviderAnalysis
from fleetpulse.assistant.providers import SYSTEM_INSTRUCTIONS, IncidentProvider, create_provider
from fleetpulse.assistant.service import AssistantService


class RecordingProvider:
    """Inspect redaction at the provider boundary without retaining raw credentials."""

    def __init__(self, provider: IncidentProvider, markers: list[str]) -> None:
        self.provider = provider
        self.name = provider.name
        self.markers = markers
        self.redaction_failures = 0

    async def analyze(self, question: str, evidence: list[EvidenceItem]) -> ProviderAnalysis:
        serialized = question + json.dumps([e.model_dump(mode="json") for e in evidence])
        self.redaction_failures = sum(marker in serialized for marker in self.markers)
        return await self.provider.analyze(question, evidence)


class FixtureProvider:
    name = "scripted-offline"

    def __init__(self, output: dict[str, Any]) -> None:
        self.output = output

    async def analyze(self, question: str, evidence: list[EvidenceItem]) -> ProviderAnalysis:
        return ProviderAnalysis.model_validate(self.output)


def ratio(values: list[bool]) -> dict[str, Any]:
    return {
        "passed": sum(values),
        "graded": len(values),
        "rate": sum(values) / len(values) if values else None,
    }


async def evaluate(
    path: Path,
    *,
    mode: str = "offline",
    limit: int | None = None,
    grades: dict[str, Any] | None = None,
) -> dict[str, Any]:
    dataset = json.loads(path.read_text())
    results = []
    settings = AssistantSettings(provider="openai") if mode == "live" else None
    for case in dataset["cases"][:limit]:
        provider: IncidentProvider = (
            FixtureProvider(case["scripted_output"])
            if mode == "offline"
            else create_provider(settings or AssistantSettings())
        )
        recorder = RecordingProvider(provider, case["forbidden_markers"])
        response = await AssistantService(recorder).analyze(
            AnalysisRequest(question=case["question"], evidence=case["evidence"])
        )
        body = response.model_dump(mode="json")
        # Stable content digest ties human grades to the exact output, not a case name alone.
        digest = hashlib.sha256(
            json.dumps(
                {
                    k: body[k]
                    for k in ("summary", "claims", "abstained", "abstention_reason", "evidence")
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()
        sources = {item.id: item.content for item in response.evidence}
        citations = [q for c in response.claims for q in c.evidence_excerpts]
        grade = (grades or {}).get(case["id"], {})
        if grade and grade.get("output_sha256") != digest:
            raise ValueError(f"Grade digest mismatch for {case['id']}")
        if mode == "offline":
            diagnosis = (
                case["labels"]["should_abstain"]
                if response.abstained
                else case["labels"]["scripted_diagnosis_correct"]
            )
            support = (
                []
                if response.abstained
                else [case["labels"]["scripted_semantic_support"]] * len(response.claims)
            )
        else:
            diagnosis = grade.get("diagnosis_correct")
            support = grade.get("claim_support", [])
            if support and len(support) != len(response.claims):
                raise ValueError("Grade one support boolean per returned claim")
            if diagnosis is not None and type(diagnosis) is not bool:
                raise ValueError("Diagnosis grade must be boolean")
            if any(type(value) is not bool for value in support):
                raise ValueError("Support grades must be booleans")
        results.append(
            {
                "id": case["id"],
                "category": case["category"],
                "output_sha256": digest,
                "response": body,
                "diagnosis_correct": diagnosis,
                "claim_support": support,
                "citation_validity": [q.evidence_id in sources for q in citations],
                "excerpt_matches": [q.excerpt in sources.get(q.evidence_id, "") for q in citations],
                "appropriate_abstention": response.abstained == case["labels"]["should_abstain"],
                "boundary_pass": response.abstained
                == case["labels"]["expected_boundary_abstention"]
                if mode == "offline"
                else None,
                "redaction_failures": recorder.redaction_failures
                + sum(marker in response.model_dump_json() for marker in case["forbidden_markers"]),
            }
        )
    return {
        "provider_configuration": (
            {
                "model": settings.model,
                "max_retries": settings.max_retries,
                "max_output_tokens": settings.max_output_tokens,
                "request_timeout_seconds": settings.request_timeout_seconds,
                "input_cost_per_million": settings.input_cost_per_million,
                "output_cost_per_million": settings.output_cost_per_million,
            }
            if settings
            else None
        ),
        "prompt_sha256": hashlib.sha256(SYSTEM_INSTRUCTIONS.encode()).hexdigest(),
        "dataset_version": dataset["version"],
        "dataset_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "split": dataset["split"],
        "mode": mode,
        "cases": len(results),
        "grading": "fixture labels; no model called"
        if mode == "offline"
        else "human grades; null means ungraded",
        "metrics": {
            "diagnosis_correctness": ratio(
                [r["diagnosis_correct"] for r in results if r["diagnosis_correct"] is not None]
            ),
            "claim_support": ratio([v for r in results for v in r["claim_support"]]),
            "citation_validity": ratio([v for r in results for v in r["citation_validity"]]),
            "excerpt_matches": ratio([v for r in results for v in r["excerpt_matches"]]),
            "appropriate_abstention": ratio([r["appropriate_abstention"] for r in results]),
            "redaction_failures": sum(r["redaction_failures"] for r in results),
            "provider_failures": sum(
                r["response"]["metrics"]["error_code"] is not None for r in results
            ),
        },
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["offline", "live"], default="offline")
    parser.add_argument("--split", choices=["development", "held-out"], default="development")
    parser.add_argument(
        "--max-calls", type=int, default=1, help="Live case limit; each case may retry"
    )
    parser.add_argument("--allow-live", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--grade-report", type=Path, help="Existing live report; never calls a model"
    )
    parser.add_argument("--grades", type=Path)
    args = parser.parse_args()
    if args.grade_report:
        if not args.grades:
            parser.error("--grade-report requires --grades")
        report = json.loads(args.grade_report.read_text())
        if report.get("mode") != "live":
            parser.error("Human live grading requires a saved live report")
        grades = json.loads(args.grades.read_text())
        for row in report["results"]:
            grade = grades.get(row["id"])
            if grade:
                if grade.get("output_sha256") != row["output_sha256"]:
                    parser.error("Grade digest does not match saved output")
                support = grade.get("claim_support", [])
                if len(support) != len(row["response"]["claims"]) or any(
                    type(v) is not bool for v in support
                ):
                    parser.error("Grade each claim with a support boolean")
                if type(grade.get("diagnosis_correct")) is not bool:
                    parser.error("Diagnosis grade must be boolean")
                row.update(diagnosis_correct=grade["diagnosis_correct"], claim_support=support)
        report["metrics"]["diagnosis_correctness"] = ratio(
            [
                r["diagnosis_correct"]
                for r in report["results"]
                if r["diagnosis_correct"] is not None
            ]
        )
        report["metrics"]["claim_support"] = ratio(
            [v for r in report["results"] for v in r["claim_support"]]
        )
    else:
        if args.mode == "live" and (not args.allow_live or not 1 <= args.max_calls <= 32):
            parser.error("Live mode requires --allow-live and --max-calls between 1 and 32")
        report = asyncio.run(
            evaluate(
                Path("evaluations/incidents-v1") / f"{args.split}.json",
                mode=args.mode,
                limit=args.max_calls if args.mode == "live" else None,
            )
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "results"}, indent=2))


if __name__ == "__main__":
    main()
