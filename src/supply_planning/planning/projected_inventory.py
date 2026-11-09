"""The projected-inventory recurrence (docs/BUSINESS_RULES.md §4, the "core
calculation of the project"):

    PI_{s,0} = OH_s
    PI_{s,t} = PI_{s,t-1} + R_{s,t} - D_{s,t}      for t = 1..13

`weeks_ahead = 0` represents the planning origin itself (before any week's
demand or receipts are applied) - it has no `week_start_date` of its own
(`None` is the legitimate value here, the same pattern as `dim_product.size`:
absent by construction, not missing data).

A week missing from `weekly_demand` raises `MissingDemandDataError` rather
than being treated as zero demand - in a real run this is where Phase 2's
forecast would eventually fill the gap for genuinely future weeks; until then,
a caller that cannot supply a real number for a required week must not guess
one (docs/ARCHITECTURE.md §2). A week missing from `weekly_confirmed_receipts`
is different: "no purchase order is due that week" is itself a known fact, so
it defaults to 0 receipts, not an error.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

HORIZON_WEEKS = 13  # docs/BUSINESS_RULES.md §3


class MissingDemandDataError(Exception):
    """Raised when a required week has no demand figure to compute with."""


@dataclass(frozen=True)
class ProjectedInventoryWeek:
    weeks_ahead: int
    week_start_date: date | None
    demand_units: int
    confirmed_receipt_units: int
    projected_inventory_units: int
    safety_stock_units: int
    projected_shortage_units: int


def compute_projected_inventory(
    *,
    on_hand_available: int,
    safety_stock_units: int,
    horizon_weeks: Sequence[date],
    weekly_demand: Mapping[date, int],
    weekly_confirmed_receipts: Mapping[date, int],
) -> list[ProjectedInventoryWeek]:
    """Run the recurrence for one SKU over `horizon_weeks` (must have exactly
    13 entries, t=1..13 in order)."""
    if len(horizon_weeks) != HORIZON_WEEKS:
        raise ValueError(f"horizon_weeks must have exactly {HORIZON_WEEKS} weeks, got {len(horizon_weeks)}")

    rows = [
        ProjectedInventoryWeek(
            weeks_ahead=0,
            week_start_date=None,
            demand_units=0,
            confirmed_receipt_units=0,
            projected_inventory_units=on_hand_available,
            safety_stock_units=safety_stock_units,
            projected_shortage_units=max(0, safety_stock_units - on_hand_available),
        )
    ]

    previous_pi = on_hand_available
    for t, week_start_date in enumerate(horizon_weeks, start=1):
        if week_start_date not in weekly_demand:
            raise MissingDemandDataError(
                f"no demand figure for {week_start_date} (week {t} of the horizon)"
            )
        demand = weekly_demand[week_start_date]
        receipts = weekly_confirmed_receipts.get(week_start_date, 0)
        projected_inventory = previous_pi + receipts - demand

        rows.append(
            ProjectedInventoryWeek(
                weeks_ahead=t,
                week_start_date=week_start_date,
                demand_units=demand,
                confirmed_receipt_units=receipts,
                projected_inventory_units=projected_inventory,
                safety_stock_units=safety_stock_units,
                projected_shortage_units=max(0, safety_stock_units - projected_inventory),
            )
        )
        previous_pi = projected_inventory

    return rows


def first_shortage_week(rows: list[ProjectedInventoryWeek]) -> int | None:
    """docs/BUSINESS_RULES.md §4.2: `first_shortage_week = min { t : PI_{s,t} < SS_s }`."""
    for row in rows:
        if row.weeks_ahead > 0 and row.projected_shortage_units > 0:
            return row.weeks_ahead
    return None
