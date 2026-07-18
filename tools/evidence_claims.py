"""Validate and render portfolio claims that are traceable to preserved evidence."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "evidence/claims.yaml"
INDEX = ROOT / "evidence/INDEX.md"
CLASSIFICATIONS = {"implemented", "measured", "evaluated", "projected", "target"}


def load_claims(path: Path = CATALOG) -> list[dict[str, Any]]:
    """Load and validate the claim catalog."""
    document = yaml.safe_load(path.read_text())
    claims = document.get("claims") if isinstance(document, dict) else None
    if not isinstance(claims, list) or not claims:
        raise ValueError("claim catalog must contain a non-empty claims list")
    seen: set[str] = set()
    for claim in claims:
        if not isinstance(claim, dict):
            raise ValueError("each claim must be an object")
        claim_id = claim.get("id")
        if not isinstance(claim_id, str) or not claim_id:
            raise ValueError("each claim needs an id")
        if claim_id in seen:
            raise ValueError(f"duplicate claim id: {claim_id}")
        seen.add(claim_id)
        if claim.get("classification") not in CLASSIFICATIONS:
            raise ValueError(f"invalid classification: {claim_id}")
        for field in ("resume_bullet", "limitations"):
            if not isinstance(claim.get(field), str) or not claim[field].strip():
                raise ValueError(f"{claim_id} needs {field}")
        evidence = claim.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise ValueError(f"{claim_id} needs evidence")
        for relative in evidence:
            if not isinstance(relative, str) or not (ROOT / relative).is_file():
                raise ValueError(f"missing evidence for {claim_id}: {relative}")
    return claims


def render_index(claims: list[dict[str, Any]]) -> str:
    """Create the human-readable evidence index from validated claims."""
    lines = [
        "# Evidence-to-claim index",
        "",
        "These portfolio-safe bullets are generated from `evidence/claims.yaml`. Every bullet",
        "links to committed evidence and states the boundary on what can be inferred.",
        "",
    ]
    for claim in claims:
        lines.extend(
            [
                f"## {claim['id']}",
                "",
                f"**Classification:** {claim['classification']}",
                "",
                f"- {claim['resume_bullet']}",
                "",
                "Evidence:",
                "",
            ]
        )
        for relative in claim["evidence"]:
            lines.append(f"- [{relative}]({relative.removeprefix('evidence/')})")
        lines.extend(["", f"Boundary: {claim['limitations']}", ""])
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-index", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    claims = load_claims()
    rendered = render_index(claims)
    if args.write_index:
        INDEX.write_text(rendered)
    elif not INDEX.is_file() or INDEX.read_text() != rendered:
        raise ValueError("evidence/INDEX.md is missing or stale; run with --write-index")
    print(f"Evidence-to-claim audit satisfied: {len(claims)} claims")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
