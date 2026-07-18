"""Phase 9 CI, supply-chain, and evidence-index contracts."""

import json
from pathlib import Path

from tools.ci_contract import runtime_image_contract, tool_image_contract, workflow_contract
from tools.evidence_claims import INDEX, load_claims, render_index
from tools.supply_chain_report import IMAGE_NAMES, summarize


def test_ci_workflow_is_immutable_and_complete() -> None:
    workflow_contract()


def test_tool_and_runtime_images_are_digest_pinned() -> None:
    tool_image_contract()
    runtime_image_contract()


def test_every_portfolio_claim_has_existing_evidence() -> None:
    claims = load_claims()
    assert len(claims) == 6
    assert INDEX.read_text() == render_index(claims)


def test_supply_chain_summary_preserves_unfixed_findings(tmp_path: Path) -> None:
    for name in IMAGE_NAMES:
        (tmp_path / f"{name}.cdx.json").write_text(
            json.dumps({"components": [{"type": "library"}, {"type": "file"}]})
        )
        (tmp_path / f"{name}.trivy.json").write_text(
            json.dumps(
                {
                    "Results": [
                        {
                            "Vulnerabilities": [
                                {"Severity": "CRITICAL", "FixedVersion": ""},
                                {"Severity": "HIGH", "FixedVersion": "2.0"},
                            ]
                        }
                    ]
                }
            )
        )
    summary = summarize(tmp_path)
    assert summary["totals"]["critical"] == 5
    assert summary["totals"]["high"] == 5
    assert summary["totals"]["fixable_high_or_critical"] == 5
    assert summary["totals"]["package_components"] == 5
