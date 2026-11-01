"""fct_inventory_snapshot generator (docs/DATA_DICTIONARY.md §5).

Simplification, stated explicitly: stock levels here are sampled independently per
product-week, scaled by the family's safety-stock target (`ASM-03`) so levels are
plausible (sometimes below target, sometimes well above it), not derived from a
full demand/supply simulation. P1.5's projected-inventory recurrence will be
validated against its own small, hand-calculated example - it does not need this
generator to be a discrete-event simulator, and building one here would be solving
a problem P1.3 does not have.

One deliberate edge case: one product-week has `allocated_qty > on_hand_qty`, the
`negative_available_stock` case `docs/DATA_DICTIONARY.md` §5 requires ingestion to
report rather than clamp to zero.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date

from .assumptions import Assumptions, DEFAULT_ASSUMPTIONS
from .product import ProductRow

SITE_ID = "WH-01"  # constant in v1, docs/BUSINESS_RULES.md §1

# Typical weekly demand magnitude per family, used only to scale a plausible stock
# level here - an independent, generator-level choice, not shared with demand.py's
# own popularity range (the two are deliberately not wired together, see module
# docstring).
_TYPICAL_WEEKLY_DEMAND: dict[str, float] = {
    "FOOT": 6.0,
    "APPAREL": 10.0,
    "PACK": 6.0,
    "NUTRI": 18.0,
}


@dataclass(frozen=True)
class InventorySnapshotRow:
    product_id: str
    site_id: str
    snapshot_date: date
    on_hand_qty: int
    allocated_qty: int


@dataclass(frozen=True)
class InventoryEdgeCases:
    negative_available_stock: tuple[str, date]


def generate_inventory_snapshots(
    products: list[ProductRow],
    week_start_dates: list[date],
    seed: int,
    *,
    assumptions: Assumptions = DEFAULT_ASSUMPTIONS,
) -> tuple[list[InventorySnapshotRow], InventoryEdgeCases]:
    """Generate one snapshot per product x week (the Monday planning origin,
    docs/DATA_DICTIONARY.md §5), with one deliberate negative-available-stock week."""
    rng = random.Random(seed)
    sorted_products = sorted(products, key=lambda p: p.product_id)
    sorted_weeks = sorted(week_start_dates)

    if len(sorted_products) < 3 or not sorted_weeks:
        raise ValueError("need at least 3 products and 1 week to place the edge case")

    negative_stock_case = (sorted_products[2].product_id, sorted_weeks[0])

    rows: list[InventorySnapshotRow] = []
    for product in sorted_products:
        safety_stock_weeks = assumptions.safety_stock_weeks[product.family]
        typical_weekly_demand = _TYPICAL_WEEKLY_DEMAND[product.family]
        target_level = safety_stock_weeks * typical_weekly_demand

        for snapshot_date in sorted_weeks:
            on_hand_qty = max(0, round(target_level * rng.uniform(0.5, 2.5)))

            if (product.product_id, snapshot_date) == negative_stock_case:
                allocated_qty = on_hand_qty + max(1, round(on_hand_qty * 0.2))
            else:
                allocated_qty = round(on_hand_qty * rng.uniform(0.0, 0.3))

            rows.append(
                InventorySnapshotRow(
                    product_id=product.product_id,
                    site_id=SITE_ID,
                    snapshot_date=snapshot_date,
                    on_hand_qty=on_hand_qty,
                    allocated_qty=allocated_qty,
                )
            )

    return rows, InventoryEdgeCases(negative_available_stock=negative_stock_case)
