"""Redaction, citation validation, abstention, and approval enforcement."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fleetpulse.assistant.models import (
    AnalysisRequest,
    AnalysisResponse,
    EvidenceInput,
    EvidenceItem,
    ProviderAnalysis,
    RemediationProposal,
    ReviewReceipt,
    ReviewRequest,
)
from fleetpulse.assistant.providers import IncidentProvider
from fleetpulse.assistant.redaction import SecretRedactor


class UnknownProposalError(ValueError):
    """Raised when a review does not match a generated proposal."""


class DuplicateReviewError(ValueError):
    """Raised when a proposal already has a human decision."""


class AssistantService:
    """Safety boundary around an untrusted analysis provider."""

    def __init__(self, provider: IncidentProvider, *, registry_limit: int = 1_000) -> None:
        self.provider = provider
        self._redactor = SecretRedactor()
        self._registry_limit = registry_limit
        self._proposals: dict[tuple[str, str], ReviewReceipt | None] = {}
        self._registry_lock = asyncio.Lock()

    async def analyze(self, request: AnalysisRequest) -> AnalysisResponse:
        """Redact provider input and fail closed on unsupported output."""
        analysis_id = f"analysis-{uuid4()}"
        evidence, redaction_count = self._prepare_evidence(request.evidence)
        question_result = self._redactor.redact(request.question)
        redaction_count += question_result.count

        if not evidence:
            return self._abstention(
                analysis_id,
                evidence,
                redaction_count,
                "No evidence was supplied.",
            )

        try:
            provider_output = await self.provider.analyze(question_result.text, evidence)
            safe_output, output_redactions = self._redact_provider_output(provider_output)
            redaction_count += output_redactions
            validation_error = self._citation_error(safe_output, evidence)
        except Exception as exc:
            return self._abstention(
                analysis_id,
                evidence,
                redaction_count,
                f"Provider output was unavailable or invalid ({type(exc).__name__}).",
            )

        if validation_error:
            return self._abstention(analysis_id, evidence, redaction_count, validation_error)

        proposals = [
            RemediationProposal(
                id=f"proposal-{index}",
                action=item.action,
                rationale=item.rationale,
                citations=item.citations,
            )
            for index, item in enumerate(safe_output.proposed_remediations, start=1)
        ]
        response = AnalysisResponse(
            analysis_id=analysis_id,
            provider=self.provider.name,
            summary=safe_output.summary,
            evidence=evidence,
            claims=safe_output.claims,
            proposed_remediations=proposals,
            abstained=safe_output.abstained,
            abstention_reason=safe_output.abstention_reason,
            redaction_count=redaction_count,
        )
        await self._register(analysis_id, proposals)
        return response

    async def review(self, request: ReviewRequest) -> ReviewReceipt:
        """Record a human decision without exposing an execution capability."""
        key = (request.analysis_id, request.proposal_id)
        async with self._registry_lock:
            if key not in self._proposals:
                raise UnknownProposalError("analysis/proposal pair was not generated here")
            if self._proposals[key] is not None:
                raise DuplicateReviewError("proposal already has a recorded decision")
            receipt = ReviewReceipt(
                review_id=f"review-{uuid4()}",
                analysis_id=request.analysis_id,
                proposal_id=request.proposal_id,
                reviewer=request.reviewer,
                decision=request.decision,
                rationale=request.rationale,
                reviewed_at=datetime.now(UTC),
            )
            self._proposals[key] = receipt
            return receipt

    def _prepare_evidence(self, inputs: list[EvidenceInput]) -> tuple[list[EvidenceItem], int]:
        evidence: list[EvidenceItem] = []
        count = 0
        for index, raw_item in enumerate(inputs, start=1):
            item = EvidenceInput.model_validate(raw_item)
            source = self._redactor.redact(item.source)
            content = self._redactor.redact(item.content)
            count += source.count + content.count
            evidence.append(
                EvidenceItem(
                    id=f"E{index}",
                    source=source.text,
                    content=content.text,
                    observed_at=item.observed_at,
                )
            )
        return evidence, count

    def _redact_provider_output(self, output: ProviderAnalysis) -> tuple[ProviderAnalysis, int]:
        redacted, count = self._redact_value(output.model_dump(mode="json"))
        return ProviderAnalysis.model_validate(redacted), count

    def _redact_value(self, value: Any) -> tuple[Any, int]:
        if isinstance(value, str):
            result = self._redactor.redact(value)
            return result.text, result.count
        if isinstance(value, list):
            output: list[Any] = []
            count = 0
            for item in value:
                safe_item, item_count = self._redact_value(item)
                output.append(safe_item)
                count += item_count
            return output, count
        if isinstance(value, dict):
            mapping: dict[str, Any] = {}
            count = 0
            for key, item in value.items():
                safe_item, item_count = self._redact_value(item)
                mapping[str(key)] = safe_item
                count += item_count
            return mapping, count
        return value, 0

    @staticmethod
    def _citation_error(output: ProviderAnalysis, evidence: list[EvidenceItem]) -> str | None:
        valid = {item.id for item in evidence}
        if output.abstained:
            if output.claims or output.proposed_remediations:
                return "Abstaining provider output contained claims or remediations."
            return None
        if not output.claims:
            return "Provider supplied no supported claims."
        cited = [citation for claim in output.claims for citation in claim.citations]
        cited += [
            citation for proposal in output.proposed_remediations for citation in proposal.citations
        ]
        unknown = sorted(set(cited) - valid)
        if unknown:
            return f"Provider cited unknown evidence identifiers: {', '.join(unknown)}."
        return None

    async def _register(self, analysis_id: str, proposals: list[RemediationProposal]) -> None:
        async with self._registry_lock:
            for proposal in proposals:
                self._proposals[(analysis_id, proposal.id)] = None
            while len(self._proposals) > self._registry_limit:
                self._proposals.pop(next(iter(self._proposals)))

    def _abstention(
        self,
        analysis_id: str,
        evidence: list[EvidenceItem],
        redaction_count: int,
        reason: str,
    ) -> AnalysisResponse:
        return AnalysisResponse(
            analysis_id=analysis_id,
            provider=self.provider.name,
            summary="The assistant abstained; inspect the evidence manually.",
            evidence=evidence,
            claims=[],
            proposed_remediations=[],
            abstained=True,
            abstention_reason=reason,
            redaction_count=redaction_count,
        )
