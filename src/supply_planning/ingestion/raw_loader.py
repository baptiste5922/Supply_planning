"""Generic "extract" step (docs/ARCHITECTURE.md §1, step 1): reads a raw-shaped
CSV and bulk-inserts its business columns into `raw.<table_name>`, stamping this
ingestion run's own metadata.

This deliberately ignores the source file's own `source_system`/`source_file`/
`extracted_at`/`load_id` columns, if it has any. P1.3's generator CSVs happen to
carry these (the generator also plays the "source" role in
`docs/ARCHITECTURE.md`'s diagram), but an extractor cannot take an ingestion
run's own metadata from the file being ingested - that would be the source
grading its own extraction. `raw` tags every row with *this* load's identity.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, MetaData, Table

_METADATA_COLUMNS = ("source_system", "source_file", "extracted_at", "load_id")


def read_business_rows(csv_path: Path) -> list[dict[str, str]]:
    """Read a raw-shaped CSV, dropping its own metadata columns (see module
    docstring) - only the remaining columns are the actual source data."""
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [{k: v for k, v in row.items() if k not in _METADATA_COLUMNS} for row in reader]


def load_raw_table(
    engine: Engine,
    *,
    table_name: str,
    rows: list[dict[str, str]],
    source_system: str,
    source_file: str,
    load_id: str,
    extracted_at: datetime | None = None,
) -> int:
    """Bulk-insert `rows` into `raw.<table_name>`, stamping ingestion metadata.
    `raw` has no constraint and no primary key on business columns
    (`sql/002_raw_tables.sql`) - this is a pure append, by design: the same
    source row can legitimately land twice across two loads."""
    if not rows:
        return 0
    extracted_at = extracted_at or datetime.now(tz=timezone.utc)

    metadata = MetaData()
    table = Table(table_name, metadata, autoload_with=engine, schema="raw")

    records: list[dict[str, Any]] = [
        {
            **row,
            "source_system": source_system,
            "source_file": source_file,
            "extracted_at": extracted_at,
            "load_id": load_id,
        }
        for row in rows
    ]
    with engine.begin() as conn:
        conn.execute(table.insert(), records)
    return len(records)
