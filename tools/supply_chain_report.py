"""Summarize CycloneDX SBOMs and Trivy image reports without hiding unfixed findings."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

IMAGE_NAMES = ("api", "worker", "outbox-relay", "agent", "assistant")


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON object from path."""
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def summarize(directory: Path) -> dict[str, Any]:
    """Return component and vulnerability counts for every application image."""
    images: dict[str, dict[str, int]] = {}
    for name in IMAGE_NAMES:
        sbom = load_json(directory / f"{name}.cdx.json")
        trivy = load_json(directory / f"{name}.trivy.json")
        vulnerabilities = [
            vulnerability
            for result in trivy.get("Results", [])
            for vulnerability in (result.get("Vulnerabilities") or [])
        ]
        high = sum(item.get("Severity") == "HIGH" for item in vulnerabilities)
        critical = sum(item.get("Severity") == "CRITICAL" for item in vulnerabilities)
        fixable = sum(bool(item.get("FixedVersion")) for item in vulnerabilities)
        components = sbom.get("components", [])
        images[name] = {
            "components_total": len(components),
            "file_components": sum(item.get("type") == "file" for item in components),
            "package_components": sum(item.get("type") != "file" for item in components),
            "high": high,
            "critical": critical,
            "fixable_high_or_critical": fixable,
        }
    return {
        "policy": (
            "Report all HIGH/CRITICAL findings and fail the gate when any has an upstream fix."
        ),
        "images": images,
        "totals": {
            "components_total": sum(item["components_total"] for item in images.values()),
            "file_components": sum(item["file_components"] for item in images.values()),
            "package_components": sum(item["package_components"] for item in images.values()),
            "high": sum(item["high"] for item in images.values()),
            "critical": sum(item["critical"] for item in images.values()),
            "fixable_high_or_critical": sum(
                item["fixable_high_or_critical"] for item in images.values()
            ),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = summarize(args.directory)
    rendered = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    print(rendered, end="")
    if args.output:
        args.output.write_text(rendered)
    return 1 if summary["totals"]["fixable_high_or_critical"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
