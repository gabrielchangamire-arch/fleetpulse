"""Enforce immutable CI, scanner, and runtime-image supply-chain references."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SHA_REF = re.compile(r"^[0-9a-f]{40}$")
DIGEST_REF = re.compile(r"@sha256:[0-9a-f]{64}$")
REQUIRED_JOBS = {
    "python-quality",
    "dependency-audit",
    "secret-scan",
    "manifest-security",
    "image-security",
    "compose-smoke",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def workflow_contract() -> None:
    path = ROOT / ".github/workflows/quality.yml"
    workflow = yaml.safe_load(path.read_text())
    jobs = workflow.get("jobs", {})
    require(set(jobs) >= REQUIRED_JOBS, "quality workflow is missing required jobs")
    require(
        workflow.get("permissions") == {"contents": "read"},
        "default permissions must read only",
    )
    require("pull_request_target" not in path.read_text(), "pull_request_target is forbidden")
    for job_name, job in jobs.items():
        require(job.get("timeout-minutes"), f"job {job_name} must have a timeout")
        for step in job.get("steps", []):
            reference = step.get("uses")
            if not reference:
                continue
            require("@" in reference, f"action reference lacks a ref: {reference}")
            owner_action, ref = reference.rsplit("@", 1)
            require(
                SHA_REF.fullmatch(ref) is not None,
                f"action must use a commit SHA: {reference}",
            )
            require(owner_action.startswith("actions/"), f"unapproved action owner: {reference}")


def tool_image_contract() -> None:
    entries: dict[str, str] = {}
    for line in (ROOT / "security/tool-images.env").read_text().splitlines():
        if line and not line.startswith("#"):
            key, value = line.split("=", 1)
            entries[key] = value
    require(
        set(entries)
        == {
            "ACTIONLINT_IMAGE",
            "KUBECONFORM_IMAGE",
            "SYFT_IMAGE",
            "TRIVY_IMAGE",
        },
        "security tool inventory drifted",
    )
    for key, reference in entries.items():
        require(DIGEST_REF.search(reference) is not None, f"{key} is not digest pinned")


def runtime_image_contract() -> None:
    for path in (
        ROOT / "agent/Dockerfile",
        ROOT / "services/api/Dockerfile",
        ROOT / "services/assistant/Dockerfile",
        ROOT / "services/outbox_relay/Dockerfile",
        ROOT / "services/worker/Dockerfile",
    ):
        first_line = path.read_text().splitlines()[0]
        require(
            DIGEST_REF.search(first_line.split()[1]) is not None,
            f"base image not pinned: {path}",
        )

    compose = yaml.safe_load((ROOT / "compose.yaml").read_text())
    for name, service in compose["services"].items():
        image = service.get("image")
        if image:
            require(DIGEST_REF.search(image) is not None, f"Compose image not pinned: {name}")

    for path in (ROOT / "deploy/kubernetes/base").glob("*.yaml"):
        for match in re.finditer(r"^\s+image:\s+(\S+)$", path.read_text(), re.MULTILINE):
            image = match.group(1)
            if not image.startswith("fleetpulse-"):
                require(
                    DIGEST_REF.search(image) is not None,
                    f"Kubernetes image not pinned: {image}",
                )


def main() -> int:
    workflow_contract()
    tool_image_contract()
    runtime_image_contract()
    print("CI and supply-chain reference contract satisfied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
