"""Tests for the P1.5 planning KPI logic (docs/BUSINESS_RULES.md §4).

The projected-inventory recurrence test below is the project's mandatory
acceptance criterion: "this recurrence... must be reproducible by hand on a
3-week example." The arithmetic is spelled out in the test's own comments so
it can be checked without running any code.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from supply_planning.planning.coverage import compute_weeks_of_cover
from supply_planning.planning.projected_inventory import (
    HORIZON_WEEKS,
    MissingDemandDataError,
    compute_projected_inventory,
    first_shortage_week,
)
from supply_planning.planning.replenishment import (
    MissingLeadTimeError,
    propose_purchase_order,
)

_ORIGIN = date(2026, 1, 5)  # an arbitrary Monday
_WEEKS = [_ORIGIN + timedelta(weeks=i) for i in range(HORIZON_WEEKS)]  # t=1..13


# --- projected_inventory.py: the mandatory hand-calculated example -----------

# OH_s = 100, SS_s = 30.
#   t=1: D=40, R=0   -> PI_1 = 100 + 0  - 40 =  60   (shortage = max(0, 30-60)  =  0)
#   t=2: D=50, R=20  -> PI_2 =  60 + 20 - 50 =  30   (shortage = max(0, 30-30)  =  0, exactly at SS - not a shortage, PI < SS is strict)
#   t=3: D=45, R=0   -> PI_3 =  30 + 0  - 45 = -15   (shortage = max(0, 30-(-15)) = 45)
# Weeks 4..13 carry no demand and no receipts, so PI stays at -15 and is not
# re-verified by hand - only t=0..3 are the acceptance-criterion example.
_HAND_DEMAND = {_WEEKS[0]: 40, _WEEKS[1]: 50, _WEEKS[2]: 45}
_HAND_RECEIPTS = {_WEEKS[1]: 20}
for _extra_week in _WEEKS[3:]:
    _HAND_DEMAND[_extra_week] = 0


def test_projected_inventory_matches_hand_calculated_example() -> None:
    rows = compute_projected_inventory(
        on_hand_available=100,
        safety_stock_units=30,
        horizon_weeks=_WEEKS,
        weekly_demand=_HAND_DEMAND,
        weekly_confirmed_receipts=_HAND_RECEIPTS,
    )

    by_week = {row.weeks_ahead: row for row in rows}
    assert by_week[0].projected_inventory_units == 100
    assert by_week[1].projected_inventory_units == 60
    assert by_week[1].projected_shortage_units == 0
    assert by_week[2].projected_inventory_units == 30
    assert by_week[2].projected_shortage_units == 0  # PI == SS is not a shortage
    assert by_week[3].projected_inventory_units == -15
    assert by_week[3].projected_shortage_units == 45

    assert first_shortage_week(rows) == 3


def test_projected_inventory_week_zero_has_no_week_start_date() -> None:
    rows = compute_projected_inventory(
        on_hand_available=100,
        safety_stock_units=30,
        horizon_weeks=_WEEKS,
        weekly_demand=_HAND_DEMAND,
        weekly_confirmed_receipts=_HAND_RECEIPTS,
    )
    assert rows[0].week_start_date is None


def test_projected_inventory_missing_demand_raises_instead_of_defaulting() -> None:
    incomplete_demand = dict(_HAND_DEMAND)
    del incomplete_demand[_WEEKS[0]]
    with pytest.raises(MissingDemandDataError):
        compute_projected_inventory(
            on_hand_available=100,
            safety_stock_units=30,
            horizon_weeks=_WEEKS,
            weekly_demand=incomplete_demand,
            weekly_confirmed_receipts=_HAND_RECEIPTS,
        )


def test_projected_inventory_missing_receipts_week_defaults_to_zero() -> None:
    """Unlike demand, a week absent from weekly_confirmed_receipts is a known
    fact ("no order due that week"), not a data-quality defect."""
    rows = compute_projected_inventory(
        on_hand_available=100,
        safety_stock_units=30,
        horizon_weeks=_WEEKS,
        weekly_demand=_HAND_DEMAND,
        weekly_confirmed_receipts={},
    )
    assert rows[1].confirmed_receipt_units == 0


def test_projected_inventory_rejects_wrong_horizon_length() -> None:
    with pytest.raises(ValueError):
        compute_projected_inventory(
            on_hand_available=100,
            safety_stock_units=30,
            horizon_weeks=_WEEKS[:5],
            weekly_demand=_HAND_DEMAND,
            weekly_confirmed_receipts={},
        )


# --- coverage.py ---------------------------------------------------------------


def test_weeks_of_cover_hand_example() -> None:
    """OH=100: week 1 (40) fits, weeks 1-2 (40+50=90) fit, weeks 1-3 (90+45=135)
    do not -> WoC = 2."""
    result = compute_weeks_of_cover(
        on_hand_available=100, horizon_weeks=_WEEKS, weekly_demand=_HAND_DEMAND
    )
    assert result.weeks_of_cover == 2
    assert result.no_forward_demand is False


def test_weeks_of_cover_zero_demand_is_capped_at_horizon_not_infinite() -> None:
    zero_demand = {week: 0 for week in _WEEKS}
    result = compute_weeks_of_cover(
        on_hand_available=100, horizon_weeks=_WEEKS, weekly_demand=zero_demand
    )
    assert result.weeks_of_cover == HORIZON_WEEKS
    assert result.no_forward_demand is True


def test_weeks_of_cover_with_negative_on_hand_is_zero_not_negative() -> None:
    result = compute_weeks_of_cover(
        on_hand_available=-5, horizon_weeks=_WEEKS, weekly_demand=_HAND_DEMAND
    )
    assert result.weeks_of_cover == 0
    assert result.no_forward_demand is False


# --- replenishment.py -----------------------------------------------------------

_LEAD_TIME_WEEKS = {"FOOT": 10, "APPAREL": 8, "PACK": 6, "NUTRI": 3}
_MOQ_UNITS = {"FOOT": 60, "APPAREL": 40, "PACK": 25, "NUTRI": 100}


def test_propose_purchase_order_returns_none_without_a_shortage() -> None:
    rows = compute_projected_inventory(
        on_hand_available=1000,
        safety_stock_units=30,
        horizon_weeks=_WEEKS,
        weekly_demand={week: 10 for week in _WEEKS},
        weekly_confirmed_receipts={},
    )
    suggestion = propose_purchase_order(
        product_id="NUTRI-001",
        family="NUTRI",
        order_reference_date=_ORIGIN,
        projected_inventory_weeks=rows,
        lead_time_weeks=_LEAD_TIME_WEEKS,
        moq_units=_MOQ_UNITS,
    )
    assert suggestion is None


def test_propose_purchase_order_missing_lead_time_is_raised_not_defaulted() -> None:
    rows = compute_projected_inventory(
        on_hand_available=100,
        safety_stock_units=30,
        horizon_weeks=_WEEKS,
        weekly_demand=_HAND_DEMAND,
        weekly_confirmed_receipts=_HAND_RECEIPTS,
    )
    incomplete_lead_times = {k: v for k, v in _LEAD_TIME_WEEKS.items() if k != "APPAREL"}
    with pytest.raises(MissingLeadTimeError):
        propose_purchase_order(
            product_id="APPAREL-001",
            family="APPAREL",
            order_reference_date=_ORIGIN,
            projected_inventory_weeks=rows,
            lead_time_weeks=incomplete_lead_times,
            moq_units=_MOQ_UNITS,
        )


def test_propose_purchase_order_feasible_when_lead_time_fits_before_shortage() -> None:
    """Shortage hits at week 3 (see the hand example); NUTRI's 3-week lead time
    arrives exactly in time."""
    rows = compute_projected_inventory(
        on_hand_available=100,
        safety_stock_units=30,
        horizon_weeks=_WEEKS,
        weekly_demand=_HAND_DEMAND,
        weekly_confirmed_receipts=_HAND_RECEIPTS,
    )
    suggestion = propose_purchase_order(
        product_id="NUTRI-001",
        family="NUTRI",
        order_reference_date=_ORIGIN,
        projected_inventory_weeks=rows,
        lead_time_weeks=_LEAD_TIME_WEEKS,
        moq_units=_MOQ_UNITS,
    )
    assert suggestion is not None
    assert suggestion.is_feasible is True
    assert suggestion.shortage_week == 3
    assert suggestion.suggested_quantity == max(45, _MOQ_UNITS["NUTRI"])


def test_propose_purchase_order_infeasible_when_lead_time_arrives_too_late() -> None:
    """The project's "no feasible plan" scenario (docs/.claude/skills/supply-
    planning): FOOT's 10-week lead time cannot possibly arrive before the
    week-3 shortage hand-calculated above - this must be visible, not hidden
    by proposing an order that looks fine but arrives too late."""
    rows = compute_projected_inventory(
        on_hand_available=100,
        safety_stock_units=30,
        horizon_weeks=_WEEKS,
        weekly_demand=_HAND_DEMAND,
        weekly_confirmed_receipts=_HAND_RECEIPTS,
    )
    suggestion = propose_purchase_order(
        product_id="FOOT-01-42",
        family="FOOT",
        order_reference_date=_ORIGIN,
        projected_inventory_weeks=rows,
        lead_time_weeks=_LEAD_TIME_WEEKS,
        moq_units=_MOQ_UNITS,
    )
    assert suggestion is not None
    assert suggestion.is_feasible is False
