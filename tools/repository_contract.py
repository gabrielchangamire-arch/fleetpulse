"""Validate the Phase 0 FleetPulse repository contract."""

from __future__ import annotations

import subprocess
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DIRECTORIES = (
    ".github/workflows",
    "agent",
    "deploy/kubernetes/base",
    "deploy/kubernetes/overlays/kind",
    "deploy/kubernetes/overlays/k3d",
    "docs/adr",
    "docs/architecture",
    "docs/runbooks",
    "docs/postmortems",
    "docs/security",
    "docs/slos",
    "drills",
    "evidence/templates",
    "load/k6",
    "migrations",
    "nginx",
    "observability/alertmanager",
    "observability/grafana",
    "observability/prometheus",
    "packages/common",
    "scripts",
    "services/api",
    "services/assistant",
    "services/outbox_relay",
    "services/worker",
    "tests",
)

REQUIRED_FILES = (
    ".github/workflows/quality.yml",
    ".env.example",
    ".gitignore",
    "CONTRIBUTING.md",
    "Makefile",
    "README.md",
    "ROADMAP.md",
    "SECURITY.md",
    "docs/architecture/repository-boundary.md",
    "docs/architecture/system.md",
    "docs/security/threat-model.md",
    "evidence/README.md",
    "pyproject.toml",
)


def git_root(path: Path) -> Path:
    """Return the resolved Git root containing path."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip()).resolve()


def contract_errors(root: Path = REPOSITORY_ROOT) -> list[str]:
    """Return all repository contract violations."""
    errors: list[str] = []
    resolved_root = root.resolve()

    if resolved_root.name != "fleetpulse":
        errors.append(f"repository directory must be named fleetpulse: {resolved_root}")
    if git_root(resolved_root) != resolved_root:
        errors.append("FleetPulse must be its own Git root")

    for relative_path in REQUIRED_DIRECTORIES:
        if not (resolved_root / relative_path).is_dir():
            errors.append(f"missing required directory: {relative_path}")

    for relative_path in REQUIRED_FILES:
        if not (resolved_root / relative_path).is_file():
            errors.append(f"missing required file: {relative_path}")

    boundary = (resolved_root / "docs/architecture/repository-boundary.md").read_text()
    if "/Users/gabriel/Documents/Fleet-Pulse" not in boundary:
        errors.append("repository boundary must explicitly identify the out-of-scope project")

    return errors


def main() -> int:
    """Print violations and return a shell-friendly status."""
    errors = contract_errors()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"Repository contract satisfied: {REPOSITORY_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
