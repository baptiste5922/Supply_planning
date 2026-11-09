"""Replenishment suggestions (docs/BUSINESS_RULES.md §2, question 2: "which
purchase orders must be placed this week, for what quantity").

This is a **suggestion**, not an automatic action - nothing here writes a
purchase order; a human decides (docs/ARCHITECTURE.md §1.2's "Odoo is
read-only" principle applies in spirit even though Phase 1 has no ERP yet).

`docs/BUSINESS_RULES.md` §4.2's missing-data rule lives here: "if the supplier
lead time is unknown, the SKU is not silently computed with a default value -
it is raised in the data-quality report with reason `missing_lead_time`."
The lead-time lookup is passed in explicitly (not read from a hard-coded
constant) precisely so this defensive branch is real code, not dead code -
`Assumptions.lead_time_weeks` always covers all four known families by
construction, but a lookup used across a whole portfolio must not assume its
caller never passes an incomplete one.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Mapping

from .projected_inventory import ProjectedInventoryWeek, first_shortage_week


@dataclass(frozen=True)
class ProposedOrder:
    product_id: str
    suggested_order_date: date
    suggested_receipt_date: date
    suggested_quantity: int
    shortage_week: int
    shortage_units: int
    is_feasible: bool
    # False when the suggested receipt date falls after the shortage week it is
    # meant to cover - docs/BUSINESS_RULES.md §2's "no feasible plan" case must
    # be visible, not hidden by proposing an order that arrives too late anyway.


class MissingLeadTimeError(Exception):
    """Raised when `family` has no entry in the lead-time lookup."""


def propose_purchase_order(
    *,
    product_id: str,
    family: str,
    order_reference_date: date,
    projected_inventory_weeks: list[ProjectedInventoryWeek],
    lead_time_weeks: Mapping[str, int],
    moq_units: Mapping[str, int],
) -> ProposedOrder | None:
    """Return a suggested order for one SKU, or `None` if no shortage is
    projected over the horizon (nothing to suggest).

    Raises `MissingLeadTimeError` if `family` is absent from `lead_time_weeks`
    - the caller is expected to catch this per SKU and report it
    (`reason_code = "missing_lead_time"`), not let one unknown family abort
    every other SKU's suggestion.
    """
    shortage_week = first_shortage_week(projected_inventory_weeks)
    if shortage_week is None:
        return None

    if family not in lead_time_weeks:
        raise MissingLeadTimeError(f"no lead time configured for family {family!r}")
    if family not in moq_units:
        raise MissingLeadTimeError(f"no MOQ configured for family {family!r}")

    shortage_row = next(
        row for row in projected_inventory_weeks if row.weeks_ahead == shortage_week
    )
    suggested_receipt_date = order_reference_date + timedelta(weeks=lead_time_weeks[family])
    suggested_quantity = max(shortage_row.projected_shortage_units, moq_units[family])

    receipt_week_offset = (suggested_receipt_date - order_reference_date).days // 7
    is_feasible = receipt_week_offset <= shortage_week

    return ProposedOrder(
        product_id=product_id,
        suggested_order_date=order_reference_date,
        suggested_receipt_date=suggested_receipt_date,
        suggested_quantity=suggested_quantity,
        shortage_week=shortage_week,
        shortage_units=shortage_row.projected_shortage_units,
        is_feasible=is_feasible,
    )
