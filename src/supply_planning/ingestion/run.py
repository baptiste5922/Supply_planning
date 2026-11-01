"""Orchestrates the full P1.4 ingestion pipeline: for each table, read the
raw-shaped CSV -> load into `raw` (append) -> validate into `clean` (upsert) ->
copy into `analytics` (docs/ARCHITECTURE.md §1).

Dimensions (`product`, `calendar`, `supplier`) load first - the fact tables'
foreign-key checks need those validated keys in hand before a single fact row
can be judged valid. The known-key sets are taken from the *validated* rows
just produced, not from a fresh query - `clean` and this run's in-memory
knowledge of it must agree by construction, not by re-reading what was just
written.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import Engine

from . import calendar as calendar_module
from . import capacity as capacity_module
from . import demand_actual as demand_actual_module
from . import inventory_snapshot as inventory_snapshot_module
from . import product as product_module
from . import purchase_order_line as purchase_order_line_module
from . import supplier as supplier_module
from .analytics_loader import copy_clean_to_analytics
from .db_writer import upsert_rows
from .quality import QualityReport
from .raw_loader import load_raw_table, read_business_rows

SOURCE_SYSTEM = "csv_sample"

PRIMARY_KEYS: dict[str, tuple[str, ...]] = {
    "product": ("product_id",),
    "calendar": ("calendar_date",),
    "supplier": ("supplier_id",),
    "demand_actual": ("product_id", "week_start_date"),
    "inventory_snapshot": ("product_id", "site_id", "snapshot_date"),
    "purchase_order_line": ("order_id", "product_id"),
    "capacity": ("site_id", "family", "week_start_date"),
}


def run_ingestion(engine: Engine, input_dir: Path, *, load_id: str | None = None) -> QualityReport:
    load_id = load_id or f"ingestion-{uuid.uuid4()}"
    extracted_at = datetime.now(tz=timezone.utc)
    report = QualityReport()

    def extract(table_name: str) -> list[dict[str, str]]:
        csv_path = input_dir / f"{table_name}.csv"
        business_rows = read_business_rows(csv_path)
        load_raw_table(
            engine,
            table_name=table_name,
            rows=business_rows,
            source_system=SOURCE_SYSTEM,
            source_file=str(csv_path),
            load_id=load_id,
            extracted_at=extracted_at,
        )
        return business_rows

    def load_clean(table_name: str, clean_rows: list[dict]) -> None:
        upsert_rows(
            engine,
            schema="clean",
            table_name=table_name,
            rows=clean_rows,
            primary_key=PRIMARY_KEYS[table_name],
        )

    # --- dimensions first ----------------------------------------------------
    product_rows = product_module.validate_rows(extract("product"), report)
    load_clean("product", product_rows)

    calendar_rows = calendar_module.validate_rows(extract("calendar"), report)
    load_clean("calendar", calendar_rows)

    supplier_rows = supplier_module.validate_rows(extract("supplier"), report)
    load_clean("supplier", supplier_rows)

    known_product_ids = {row["product_id"] for row in product_rows}
    known_calendar_dates = {row["calendar_date"] for row in calendar_rows}
    known_supplier_ids = {row["supplier_id"] for row in supplier_rows}

    # --- facts, depend on the dimensions above --------------------------------
    demand_rows = demand_actual_module.validate_rows(
        extract("demand_actual"),
        report,
        known_product_ids=known_product_ids,
        known_calendar_dates=known_calendar_dates,
    )
    load_clean("demand_actual", demand_rows)

    inventory_rows = inventory_snapshot_module.validate_rows(
        extract("inventory_snapshot"),
        report,
        known_product_ids=known_product_ids,
        known_calendar_dates=known_calendar_dates,
    )
    load_clean("inventory_snapshot", inventory_rows)

    po_rows = purchase_order_line_module.validate_rows(
        extract("purchase_order_line"),
        report,
        known_product_ids=known_product_ids,
        known_supplier_ids=known_supplier_ids,
    )
    load_clean("purchase_order_line", po_rows)

    capacity_rows = capacity_module.validate_rows(
        extract("capacity"), report, known_calendar_dates=known_calendar_dates
    )
    load_clean("capacity", capacity_rows)

    # --- analytics, straight copy from clean (docs/ARCHITECTURE.md §3) -------
    for table_name, primary_key in PRIMARY_KEYS.items():
        copy_clean_to_analytics(engine, clean_table_name=table_name, primary_key=primary_key)

    return report
