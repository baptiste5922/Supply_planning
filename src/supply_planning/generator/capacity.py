"""fct_capacity generator (docs/DATA_DICTIONARY.md §7).

`available_capacity_units` is a pure computation (`ASM-05` x `ASM-11`), not
randomised: it is the warehouse's configured capacity, not an observed fact.
`planned_load_units` is sampled, since it represents "what the demand/supply plan
asked the warehouse to do that week" and P1.3 runs before P1.5 produces a real
plan - one deliberate edge case forces a single family-week above 100% (docs/
BUSINESS_RULES.md §4.3's "overload is not capped" case), the rest stay plausibly
under capacity.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date

from .assumptions import FAMILIES, Assumptions, DEFAULT_ASSUMPTIONS

SITE_ID = "WH-01"  # constant in v1, docs/BUSINESS_RULES.md §1


@dataclass(frozen=True)
class CapacityRow:
    site_id: str
    family: str
    week_start_date: date
    available_capacity_units: int
    planned_load_units: int


@dataclass(frozen=True)
class CapacityEdgeCases:
    overload: tuple[str, str, date]  # (site_id, family, week_start_date)


def generate_capacity(
    week_start_dates: list[date],
    seed: int,
    *,
    assumptions: Assumptions = DEFAULT_ASSUMPTIONS,
) -> tuple[list[CapacityRow], CapacityEdgeCases]:
    """Generate one `fct_capacity` row per family x week, with one family-week
    deliberately overloaded (planned_load_units > available_capacity_units)."""
    rng = random.Random(seed)
    sorted_weeks = sorted(week_start_dates)
    if not sorted_weeks:
        raise ValueError("need at least 1 week to generate capacity")

    overload_family = "FOOT"
    overload_week = sorted_weeks[len(sorted_weeks) // 2]

    rows: list[CapacityRow] = []
    for family in FAMILIES:
        available = round(
            assumptions.total_capacity_units_per_week * assumptions.capacity_share[family]
        )
        for week_start in sorted_weeks:
            if family == overload_family and week_start == overload_week:
                planned_load = round(available * rng.uniform(1.1, 1.3))
            else:
                planned_load = round(available * rng.uniform(0.6, 0.95))

            rows.append(
                CapacityRow(
                    site_id=SITE_ID,
                    family=family,
                    week_start_date=week_start,
                    available_capacity_units=available,
                    planned_load_units=planned_load,
                )
            )

    edge_cases = CapacityEdgeCases(overload=(SITE_ID, overload_family, overload_week))
    return rows, edge_cases
