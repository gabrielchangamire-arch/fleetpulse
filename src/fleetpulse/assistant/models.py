"""Typed contracts for cited incident analysis and human review."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """Reject unexpected provider and API fields."""

    model_config = ConfigDict(extra="forbid")


class EvidenceInput(StrictModel):
    """One bounded item of untrusted incident evidence."""

    source: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=20_000)
    observed_at: datetime | None = None


class EvidenceItem(StrictModel):
    """Evidence after canonical IDs and redaction are applied."""

    id: str
    source: str
    content: str
    observed_at: datetime | None = None


class AnalysisRequest(StrictModel):
    """A question scoped only to caller-supplied evidence."""

    question: str = Field(min_length=1, max_length=2_000)
    evidence: list[EvidenceInput] = Field(max_length=50)


class Claim(StrictModel):
    """A factual statement with evidence identifiers."""

    text: str = Field(min_length=1, max_length=2_000)
    citations: list[str] = Field(min_length=1, max_length=20)


class ProviderRemediation(StrictModel):
    """Provider-generated text that can only become a proposal."""

    action: str = Field(min_length=1, max_length=2_000)
    rationale: str = Field(min_length=1, max_length=2_000)
    citations: list[str] = Field(min_length=1, max_length=20)


class ProviderAnalysis(StrictModel):
    """Strict provider output before FleetPulse safety validation."""

    summary: str = Field(max_length=4_000)
    claims: list[Claim] = Field(max_length=50)
    proposed_remediations: list[ProviderRemediation] = Field(max_length=20)
    abstained: bool
    abstention_reason: str | None = Field(max_length=2_000)


class RemediationProposal(ProviderRemediation):
    """A non-executing proposal that always needs a human decision."""

    id: str
    approval_status: Literal["requires_human_approval"] = "requires_human_approval"


class SafetyBoundary(StrictModel):
    """Machine-readable reminder of the assistant's authority."""

    read_only: Literal[True] = True
    can_execute: Literal[False] = False
    approval_required: Literal[True] = True


class AnalysisResponse(StrictModel):
    """Validated, redacted output returned to an operator."""

    analysis_id: str
    provider: str
    summary: str
    evidence: list[EvidenceItem]
    claims: list[Claim]
    proposed_remediations: list[RemediationProposal]
    abstained: bool
    abstention_reason: str | None
    redaction_count: int
    safety: SafetyBoundary = Field(default_factory=SafetyBoundary)


class ReviewRequest(StrictModel):
    """Explicit human decision about one proposal."""

    analysis_id: str = Field(min_length=1, max_length=100)
    proposal_id: str = Field(min_length=1, max_length=100)
    reviewer: str = Field(min_length=1, max_length=200)
    decision: Literal["approved", "rejected"]
    rationale: str = Field(min_length=1, max_length=2_000)


class ReviewReceipt(StrictModel):
    """Audit receipt; approval still does not execute an action."""

    review_id: str
    analysis_id: str
    proposal_id: str
    reviewer: str
    decision: Literal["approved", "rejected"]
    rationale: str
    reviewed_at: datetime
    execution_available: Literal[False] = False
