"""`supplier` (`dim_supplier`) validation: `raw.supplier` -> `clean.supplier`
(docs/DATA_DICTIONARY.md §3). A root dimension: only presence and uniqueness of
`supplier_id` matter here.
"""

from __future__ import annotations

from typing import Any

from .quality import IssueKind, QualityIssue, QualityReport
from .validators import parse_required_text

TABLE_NAME = "supplier"


def _find_duplicate_keys(raw_rows: list[dict[str, str]]) -> set[tuple[str, ...]]:
    seen: set[tuple[str, ...]] = set()
    duplicates: set[tuple[str, ...]] = set()
    for raw_row in raw_rows:
        key = (raw_row.get("supplier_id") or "",)
        if key in seen:
            duplicates.add(key)
        seen.add(key)
    return duplicates


def validate_rows(raw_rows: list[dict[str, str]], report: QualityReport) -> list[dict[str, Any]]:
    report.rows_read[TABLE_NAME] = report.rows_read.get(TABLE_NAME, 0) + len(raw_rows)
    duplicate_keys = _find_duplicate_keys(raw_rows)

    clean_rows: list[dict[str, Any]] = []
    for raw_row in raw_rows:
        key = (raw_row.get("supplier_id") or "",)

        if key in duplicate_keys:
            report.add(
                QualityIssue(
                    TABLE_NAME, IssueKind.REJECTED, "duplicate_key", key,
                    f"supplier_id {raw_row.get('supplier_id')!r} appears more than once",
                )
            )
            continue

        supplier_id, id_error = parse_required_text(raw_row.get("supplier_id"), "supplier_id")
        supplier_name, name_error = parse_required_text(raw_row.get("supplier_name"), "supplier_name")

        errors = [e for e in (id_error, name_error) if e]
        if errors:
            report.add(
                QualityIssue(TABLE_NAME, IssueKind.REJECTED, "invalid_supplier", key, "; ".join(errors))
            )
            continue

        clean_rows.append({"supplier_id": supplier_id, "supplier_name": supplier_name})

    report.rows_loaded[TABLE_NAME] = len(clean_rows)
    return clean_rows
