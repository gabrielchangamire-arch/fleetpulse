"""Pure helpers for controlled reliability drill evidence."""

from __future__ import annotations

import math


def nearest_rank_percentile(values: list[float], percentile: float) -> float:
    """Return the nearest-rank percentile without inventing interpolated samples."""
    if not values:
        raise ValueError("at least one value is required")
    if not 0 < percentile <= 100:
        raise ValueError("percentile must be greater than 0 and at most 100")
    ordered = sorted(values)
    rank = math.ceil(percentile / 100 * len(ordered))
    return ordered[rank - 1]
