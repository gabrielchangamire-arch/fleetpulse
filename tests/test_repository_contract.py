"""Tests for the repository's Phase 0 invariants."""

from pathlib import Path

from fleetpulse_project import __version__
from tools.repository_contract import REPOSITORY_ROOT, contract_errors, git_root


def test_repository_contract_is_satisfied() -> None:
    assert contract_errors() == []


def test_repository_is_an_independent_git_root() -> None:
    assert git_root(REPOSITORY_ROOT) == REPOSITORY_ROOT.resolve()
    assert REPOSITORY_ROOT.name == "fleetpulse"


def test_existing_fleet_pulse_project_is_outside_repository() -> None:
    existing_project = Path("/Users/gabriel/Documents/Fleet-Pulse").resolve()
    assert existing_project != REPOSITORY_ROOT.resolve()
    assert REPOSITORY_ROOT.resolve() not in existing_project.parents
    assert existing_project not in REPOSITORY_ROOT.resolve().parents


def test_package_version_is_explicit() -> None:
    assert __version__ == "0.1.0"
