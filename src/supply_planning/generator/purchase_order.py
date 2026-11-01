"""fct_purchase_order_line generator (docs/DATA_DICTIONARY.md §6).

Simplification, stated explicitly: this generator does not simulate a full
multi-year ordering cadence (reorder points, varying order sizes over time). It
produces a small, fixed number of order-lines per SKU - enough to exercise every
`status` value and every OTIF outcome (`docs/BUSINESS_RULES.md` §4.4) at least
once, which is what P1.4/P1.5 need to test against. A production-volume ordering
simulation is out of scope for a "small sample fixture" (P1.3 deliverable).

Each product gets two lines, built from a deterministic rotation of named cases so
every status and OTIF outcome appears across the dataset without relying on luck:
  - most lines: received in full, exactly on the promised date (OTIF success,
    the common case a real warehouse should look like most of the time);
  - one rotation slot each for: late-but-full, early-but-full (the delivery
    tolerance is 0 days per `ASM-06`, so early also fails OTIF), partial receipt,
    `cancelled_by_alpiflow`, `cancelled_by_supplier`, an order still open
    (`confirmed`, nothing received yet) and a `draft` order.

One further edge case, injected at the very first generated line: a missing
`promised_receipt_date`. `docs/DATA_DICTIONARY.md` §6 requires this to be reported
by ingestion, never defaulted - the clean/analytics schema's `NOT NULL` constraint
would reject it outright, so this malformed state can only exist in `raw`
(docs/ARCHITECTURE.md §3: raw holds what the source said, even if malformed).
`promised_receipt_date` is therefore typed `date | None` here, not because `None`
is a valid business value, but because raw-shaped source data can be wrong.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, timedelta

from .assumptions import Assumptions, DEFAULT_ASSUMPTIONS
from .product import ProductRow

_SUPPLIERS_BY_FAMILY: dict[str, tuple[str, ...]] = {
    "FOOT": ("SUP-02",),  # Dolomiti Footwear Group
    "APPAREL": ("SUP-01",),  # Pyrenees Textile Co.
    "PACK": ("SUP-05", "SUP-06"),  # Alps Gear Manufacturing / Cevennes Pack & Carry
    "NUTRI": ("SUP-03", "SUP-04"),  # Massif Central Outdoor Supply / Nordic Trail Nutrition
}

_LATE_DAYS = 5
_EARLY_DAYS = 3
_PARTIAL_RECEIVED_FRACTION = 0.6

# (status, days_offset_from_promised | None if no receipt, received_qty_fraction | None)
_CASE_ROTATION: tuple[tuple[str, str, int | None, float | None], ...] = (
    ("on_time_full", "received", 0, 1.0),
    ("on_time_full", "received", 0, 1.0),
    ("on_time_full", "received", 0, 1.0),
    ("late_full", "received", _LATE_DAYS, 1.0),
    ("early_full", "received", -_EARLY_DAYS, 1.0),
    ("partial", "partially_received", 0, _PARTIAL_RECEIVED_FRACTION),
    ("cancelled_by_alpiflow", "cancelled_by_alpiflow", None, 0.0),
    ("cancelled_by_supplier", "cancelled_by_supplier", None, 0.0),
    ("still_open", "confirmed", None, None),
    ("draft", "draft", None, None),
)


@dataclass(frozen=True)
class PurchaseOrderLineRow:
    order_id: str
    product_id: str
    supplier_id: str
    order_date: date
    promised_receipt_date: date | None  # None only for the deliberate malformed case
    actual_receipt_date: date | None
    ordered_qty: int
    received_qty: int | None
    status: str


@dataclass(frozen=True)
class PurchaseOrderEdgeCases:
    missing_promised_date: str  # order_id


def generate_purchase_order_lines(
    products: list[ProductRow],
    week_start_dates: list[date],
    seed: int,
    *,
    assumptions: Assumptions = DEFAULT_ASSUMPTIONS,
) -> tuple[list[PurchaseOrderLineRow], PurchaseOrderEdgeCases]:
    """Generate two `fct_purchase_order_line` rows per product (see module docstring
    for why two, and for the case rotation each product's two lines are drawn from)."""
    rng = random.Random(seed)
    sorted_products = sorted(products, key=lambda p: p.product_id)
    sorted_weeks = sorted(week_start_dates)
    if len(sorted_weeks) < 2:
        raise ValueError("need at least 2 weeks of history to place two orders per product")

    order_week_indexes = (
        max(0, round(len(sorted_weeks) * 0.15)),
        min(len(sorted_weeks) - 1, round(len(sorted_weeks) * 0.6)),
    )

    rows: list[PurchaseOrderLineRow] = []
    missing_promised_date_order_id: str | None = None
    order_counter = 0

    for product_index, product in enumerate(sorted_products):
        lead_time_weeks = assumptions.lead_time_weeks[product.family]
        moq = assumptions.moq_units[product.family]
        suppliers = _SUPPLIERS_BY_FAMILY[product.family]
        supplier_id = suppliers[product_index % len(suppliers)]

        for line_index, week_index in enumerate(order_week_indexes):
            order_counter += 1
            order_id = f"PO-{order_counter:05d}"
            order_date = sorted_weeks[week_index]
            promised_receipt_date: date | None = order_date + timedelta(weeks=lead_time_weeks)
            ordered_qty = moq * rng.choice([1, 2, 3])

            case_index = (product_index * 2 + line_index) % len(_CASE_ROTATION)
            _case_name, status, days_offset, received_fraction = _CASE_ROTATION[case_index]

            if days_offset is None or received_fraction is None:
                actual_receipt_date = None
                received_qty = 0 if status.startswith("cancelled") else None
            else:
                actual_receipt_date = promised_receipt_date + timedelta(days=days_offset)
                received_qty = round(ordered_qty * received_fraction)

            if order_counter == 1:
                # The one deliberately malformed row (see module docstring): the
                # promised date is simply unknown, everything else about the
                # receipt still happened as normal.
                promised_receipt_date = None
                missing_promised_date_order_id = order_id

            rows.append(
                PurchaseOrderLineRow(
                    order_id=order_id,
                    product_id=product.product_id,
                    supplier_id=supplier_id,
                    order_date=order_date,
                    promised_receipt_date=promised_receipt_date,
                    actual_receipt_date=actual_receipt_date,
                    ordered_qty=ordered_qty,
                    received_qty=received_qty,
                    status=status,
                )
            )

    assert missing_promised_date_order_id is not None  # at least one product exists
    return rows, PurchaseOrderEdgeCases(missing_promised_date=missing_promised_date_order_id)
