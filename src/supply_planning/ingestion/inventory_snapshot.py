"""`inventory_snapshot` (`fct_inventory_snapshot`) validation:
`raw.inventory_snapshot` -> `clean.inventory_snapshot` (docs/DATA_DICTIONARY.md §5).

`available_qty = on_hand_qty - allocated_qty` is never stored
(docs/DATA_DICTIONARY.md §5) - it is checked here only to decide whether to
FLAG the row. A negative result is **not** rejected and **not** clamped to
zero: the row is loaded as-is, and the data-quality report also gets a
`negative_available_stock` entry, because it signals a real planning problem
(bad allocation or stale snapshot) a planner must see, not a parsing failure.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from .quality import IssueKind, QualityIssue, QualityReport
from .validators import parse_date, parse_int, parse_required_text

TABLE_NAME = "inventory_snapshot"


def _find_duplicate_keys(raw_rows: list[dict[str, str]]) -> set[tuple[str, ...]]:
    seen: set[tuple[str, ...]] = set()
    duplicates: set[tuple[str, ...]] = set()
    for raw_row in raw_rows:
        key = (
            raw_row.get("product_id") or "",
            raw_row.get("site_id") or "",
            raw_row.get("snapshot_date") or "",
        )
        if key in seen:
            duplicates.add(key)
        seen.add(key)
    return duplicates


def validate_rows(
    raw_rows: list[dict[str, str]],
    report: QualityReport,
    *,
    known_product_ids: set[str],
    known_calendar_dates: set[date],
) -> list[dict[str, Any]]:
    report.rows_read[TABLE_NAME] = report.rows_read.get(TABLE_NAME, 0) + len(raw_rows)
    duplicate_keys = _find_duplicate_keys(raw_rows)

    clean_rows: list[dict[str, Any]] = []
    for raw_row in raw_rows:
        key = (
            raw_row.get("product_id") or "",
            raw_row.get("site_id") or "",
            raw_row.get("snapshot_date") or "",
        )

        if key in duplicate_keys:
            report.add(
                QualityIssue(
                    TABLE_NAME, IssueKind.REJECTED, "duplicate_key", key,
                    f"{key} appears more than once in this batch",
                )
            )
            continue

        product_id = (raw_row.get("product_id") or "").strip()
        site_id, site_error = parse_required_text(raw_row.get("site_id"), "site_id")
        on_hand_qty, on_hand_error = parse_int(raw_row.get("on_hand_qty"), "on_hand_qty", minimum=0)
        allocated_qty, allocated_error = parse_int(
            raw_row.get("allocated_qty"), "allocated_qty", minimum=0
        )

        snapshot_date, date_error = parse_date(raw_row.get("snapshot_date"), "snapshot_date")

        errors = [e for e in (site_error, on_hand_error, allocated_error, date_error) if e]
        if not product_id:
            errors.append("product_id is missing")
        elif product_id not in known_product_ids:
            errors.append(f"unknown product_id {product_id!r} (not in clean.product)")
        if snapshot_date is not None and snapshot_date not in known_calendar_dates:
            errors.append(f"unknown snapshot_date {snapshot_date} (not in clean.calendar)")

        if errors:
            report.add(
                QualityIssue(
                    TABLE_NAME, IssueKind.REJECTED, "invalid_inventory_snapshot", key, "; ".join(errors)
                )
            )
            continue

        if allocated_qty > on_hand_qty:
            report.add(
                QualityIssue(
                    TABLE_NAME,
                    IssueKind.FLAGGED,
                    "negative_available_stock",
                    key,
                    f"allocated_qty ({allocated_qty}) > on_hand_qty ({on_hand_qty})",
                )
            )

        clean_rows.append(
            {
                "product_id": product_id,
                "site_id": site_id,
                "snapshot_date": snapshot_date,
                "on_hand_qty": on_hand_qty,
                "allocated_qty": allocated_qty,
            }
        )

    report.rows_loaded[TABLE_NAME] = len(clean_rows)
    return clean_rows
