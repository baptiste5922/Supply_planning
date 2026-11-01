"""Generic idempotent writer for `clean` and `analytics` (same mechanics, only
the schema name differs - docs/ARCHITECTURE.md §3).

`docs/ARCHITECTURE.md` §5: "Idempotent loads. Re-running an ingestion must not
duplicate rows... the duplicate is rejected by a constraint, not by a
convention." `clean`/`analytics` tables have a real primary key, so re-running
the same load with `INSERT ... ON CONFLICT DO UPDATE` is safe: a re-run
overwrites each row with the same values, no duplicate row is created.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Engine, MetaData, Table
from sqlalchemy.dialects.postgresql import insert as pg_insert


def upsert_rows(
    engine: Engine,
    *,
    schema: str,
    table_name: str,
    rows: list[dict[str, Any]],
    primary_key: tuple[str, ...],
) -> int:
    if not rows:
        return 0

    metadata = MetaData()
    table = Table(table_name, metadata, autoload_with=engine, schema=schema)

    insert_stmt = pg_insert(table).values(rows)
    update_columns = {
        column.name: insert_stmt.excluded[column.name]
        for column in table.columns
        if column.name not in primary_key
    }
    stmt = insert_stmt.on_conflict_do_update(index_elements=list(primary_key), set_=update_columns)

    with engine.begin() as conn:
        conn.execute(stmt)
    return len(rows)
