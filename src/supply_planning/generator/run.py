"""Orchestrates the full P1.3 synthetic dataset and writes it as raw-shaped CSVs.

Calls every table generator against one shared calendar/product/supplier base, then
writes one CSV per table under `sql/002_raw_tables.sql`'s column names, plus
ingestion metadata (`source_system`, `source_file`, `extracted_at`, `load_id` -
docs/ARCHITECTURE.md §3). File names follow the `raw` table names exactly
(`product.csv`, `demand_actual.csv`, ...) rather than the illustrative names in
`docs/ARCHITECTURE.md`'s diagram, which predate P1.2's finalised schema.

A missing value (the one deliberate `was None` edge case in purchase orders) is
written as an empty CSV field - "the source did not provide this", for P1.4's
ingestion to interpret, not the literal text "None".
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, fields
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from .assumptions import Assumptions, DEFAULT_ASSUMPTIONS
from .calendar import generate_calendar
from .capacity import CapacityEdgeCases, generate_capacity
from .demand import DemandEdgeCases, generate_demand
from .inventory import InventoryEdgeCases, generate_inventory_snapshots
from .product import generate_products
from .purchase_order import PurchaseOrderEdgeCases, generate_purchase_order_lines
from .supplier import generate_suppliers

SOURCE_SYSTEM = "synthetic_generator"


@dataclass(frozen=True)
class EdgeCases:
    demand: DemandEdgeCases
    inventory: InventoryEdgeCases
    purchase_order: PurchaseOrderEdgeCases
    capacity: CapacityEdgeCases


@dataclass(frozen=True)
class GeneratedDataset:
    """Every table's rows, raw-shaped, plus where the deliberate edge cases ended up."""

    product: list[Any]
    calendar: list[Any]
    supplier: list[Any]
    demand_actual: list[Any]
    inventory_snapshot: list[Any]
    purchase_order_line: list[Any]
    capacity: list[Any]
    edge_cases: EdgeCases


def generate_all(
    seed: int,
    start_date: date,
    end_date: date,
    *,
    assumptions: Assumptions = DEFAULT_ASSUMPTIONS,
) -> GeneratedDataset:
    """Generate every table for one deterministic dataset.

    The same `seed`, `start_date`, `end_date` and `assumptions` always produce the
    same rows (P1.3 acceptance criterion) - every table generator is a pure
    function of its inputs, no hidden `date.today()` inside.
    """
    calendar_rows = generate_calendar(start_date, end_date)
    week_start_dates = sorted({row.week_start_date for row in calendar_rows})

    products = generate_products(seed=seed)
    suppliers = generate_suppliers()

    demand_rows, demand_edges = generate_demand(
        products, week_start_dates, seed=seed, assumptions=assumptions
    )
    inventory_rows, inventory_edges = generate_inventory_snapshots(
        products, week_start_dates, seed=seed, assumptions=assumptions
    )
    po_rows, po_edges = generate_purchase_order_lines(
        products, week_start_dates, seed=seed, assumptions=assumptions
    )
    capacity_rows, capacity_edges = generate_capacity(
        week_start_dates, seed=seed, assumptions=assumptions
    )

    return GeneratedDataset(
        product=products,
        calendar=calendar_rows,
        supplier=suppliers,
        demand_actual=demand_rows,
        inventory_snapshot=inventory_rows,
        purchase_order_line=po_rows,
        capacity=capacity_rows,
        edge_cases=EdgeCases(
            demand=demand_edges,
            inventory=inventory_edges,
            purchase_order=po_edges,
            capacity=capacity_edges,
        ),
    )


def _row_to_csv_dict(
    row: Any, *, source_file: str, extracted_at: datetime, load_id: str
) -> dict[str, str]:
    record: dict[str, str] = {}
    for f in fields(row):
        value = getattr(row, f.name)
        record[f.name] = "" if value is None else str(value)
    record["source_system"] = SOURCE_SYSTEM
    record["source_file"] = source_file
    record["extracted_at"] = extracted_at.isoformat()
    record["load_id"] = load_id
    return record


def write_raw_csvs(
    dataset: GeneratedDataset,
    output_dir: Path,
    *,
    load_id: str,
    extracted_at: datetime | None = None,
) -> None:
    """Write one CSV per table, raw-shaped, under `output_dir`."""
    extracted_at = extracted_at or datetime.now(tz=timezone.utc)
    output_dir.mkdir(parents=True, exist_ok=True)

    tables: dict[str, list[Any]] = {
        "product": dataset.product,
        "calendar": dataset.calendar,
        "supplier": dataset.supplier,
        "demand_actual": dataset.demand_actual,
        "inventory_snapshot": dataset.inventory_snapshot,
        "purchase_order_line": dataset.purchase_order_line,
        "capacity": dataset.capacity,
    }

    for table_name, rows in tables.items():
        source_file = f"{table_name}.csv"
        output_path = output_dir / source_file
        business_fields = [f.name for f in fields(rows[0])] if rows else []
        fieldnames = business_fields + ["source_system", "source_file", "extracted_at", "load_id"]

        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    _row_to_csv_dict(
                        row, source_file=source_file, extracted_at=extracted_at, load_id=load_id
                    )
                )
