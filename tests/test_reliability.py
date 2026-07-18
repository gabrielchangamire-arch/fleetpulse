"""Tests for reliability evidence calculations."""

from __future__ import annotations

import pytest

from fleetpulse_project.reliability import nearest_rank_percentile


def test_nearest_rank_percentile_uses_observed_value() -> None:
    assert nearest_rank_percentile([5, 1, 3, 2, 4], 95) == 5
    assert nearest_rank_percentile([1, 2, 3, 4, 5], 50) == 3


def test_nearest_rank_percentile_rejects_invalid_input() -> None:
    with pytest.raises(ValueError, match="at least one"):
        nearest_rank_percentile([], 95)
    with pytest.raises(ValueError, match="percentile"):
        nearest_rank_percentile([1], 0)
