"""Weeks of cover (docs/BUSINESS_RULES.md §4.1):

    WoC_s = max { k in [0, 13] : sum_{t=1..k} D_{s,t} <= OH_s }

Forward-looking demand only - no receipts (coverage measures the starting
position; the full plan with receipts is `projected_inventory.py`'s job).

Zero-demand handling is explicit, not incidental: if cumulative demand over
the whole horizon is zero, coverage is capped at 13 and `no_forward_demand`
is set - never returned as infinite, never a silent `None`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from .projected_inventory import HORIZON_WEEKS, MissingDemandDataError


@dataclass(frozen=True)
class CoverageResult:
    weeks_of_cover: int
    no_forward_demand: bool


def compute_weeks_of_cover(
    *,
    on_hand_available: int,
    horizon_weeks: Sequence[date],
    weekly_demand: Mapping[date, int],
) -> CoverageResult:
    if len(horizon_weeks) != HORIZON_WEEKS:
        raise ValueError(f"horizon_weeks must have exactly {HORIZON_WEEKS} weeks, got {len(horizon_weeks)}")

    demands: list[int] = []
    for week_start_date in horizon_weeks:
        if week_start_date not in weekly_demand:
            raise MissingDemandDataError(f"no demand figure for {week_start_date}")
        demands.append(weekly_demand[week_start_date])

    if sum(demands) == 0:
        return CoverageResult(weeks_of_cover=HORIZON_WEEKS, no_forward_demand=True)

    cumulative = 0
    weeks_of_cover = 0
    for k, demand in enumerate(demands, start=1):
        cumulative += demand
        if cumulative > on_hand_available:
            break
        weeks_of_cover = k

    return CoverageResult(weeks_of_cover=weeks_of_cover, no_forward_demand=False)
