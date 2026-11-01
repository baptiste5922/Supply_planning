"""`clean` -> `analytics` copy (docs/ARCHITECTURE.md §3): the two schemas share
the same shape in v1 - no transformation exists yet to justify a difference
(`sql/004_analytics_tables.sql`'s own comment). This is therefore a plain copy
of already-validated rows, not a second validation pass - `clean` already did
the validating; `analytics` only renames the table (`dim_`/`fct_` prefixes).
"""

from __future__ import annotations

from sqlalchemy import Engine, MetaData, Table, select

from .db_writer import upsert_rows

ANALYTICS_TABLE_NAMES: dict[str, str] = {
    "product": "dim_product",
    "calendar": "dim_calendar",
    "supplier": "dim_supplier",
    "demand_actual": "fct_demand_actual",
    "inventory_snapshot": "fct_inventory_snapshot",
    "purchase_order_line": "fct_purchase_order_line",
    "capacity": "fct_capacity",
}


def copy_clean_to_analytics(
    engine: Engine, *, clean_table_name: str, primary_key: tuple[str, ...]
) -> int:
    metadata = MetaData()
    clean_table = Table(clean_table_name, metadata, autoload_with=engine, schema="clean")

    with engine.connect() as conn:
        rows = [dict(row._mapping) for row in conn.execute(select(clean_table))]

    analytics_table_name = ANALYTICS_TABLE_NAMES[clean_table_name]
    return upsert_rows(
        engine, schema="analytics", table_name=analytics_table_name, rows=rows, primary_key=primary_key
    )
