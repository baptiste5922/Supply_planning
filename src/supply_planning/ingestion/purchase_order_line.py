"""`purchase_order_line` (`fct_purchase_order_line`) validation:
`raw.purchase_order_line` -> `clean.purchase_order_line`
(docs/DATA_DICTIONARY.md §6).

A missing `promised_receipt_date` is rejected **regardless of `status`**: the
`clean` schema's `NOT NULL` constraint (`sql/003_clean_tables.sql`) requires it
unconditionally, so a row without one cannot reach `clean` under any status.
`docs/DATA_DICTIONARY.md` §6 calls out `confirmed`/`partially_received`/
`received` specifically because that is where the *business* impact is (the
OTIF and shortage calculations must exclude such a row) - which calculations
exclude a line is a P1.5 concern; ingestion's job is only to decide whether the
row is loadable at all, and a `NULL` date never is.
"""

from __future__ import annotations

from typing import Any

from .quality import IssueKind, QualityIssue, QualityReport
from .validators import check_in_set, parse_date, parse_int, parse_optional_date, parse_optional_int

TABLE_NAME = "purchase_order_line"
ALLOWED_STATUSES = (
    "draft",
    "confirmed",
    "partially_received",
    "received",
    "cancelled_by_alpiflow",
    "cancelled_by_supplier",
)


def _find_duplicate_keys(raw_rows: list[dict[str, str]]) -> set[tuple[str, ...]]:
    seen: set[tuple[str, ...]] = set()
    duplicates: set[tuple[str, ...]] = set()
    for raw_row in raw_rows:
        key = (raw_row.get("order_id") or "", raw_row.get("product_id") or "")
        if key in seen:
            duplicates.add(key)
        seen.add(key)
    return duplicates


def validate_rows(
    raw_rows: list[dict[str, str]],
    report: QualityReport,
    *,
    known_product_ids: set[str],
    known_supplier_ids: set[str],
) -> list[dict[str, Any]]:
    report.rows_read[TABLE_NAME] = report.rows_read.get(TABLE_NAME, 0) + len(raw_rows)
    duplicate_keys = _find_duplicate_keys(raw_rows)

    clean_rows: list[dict[str, Any]] = []
    for raw_row in raw_rows:
        key = (raw_row.get("order_id") or "", raw_row.get("product_id") or "")

        if key in duplicate_keys:
            report.add(
                QualityIssue(
                    TABLE_NAME, IssueKind.REJECTED, "duplicate_key", key,
                    f"{key} appears more than once in this batch",
                )
            )
            continue

        order_id = (raw_row.get("order_id") or "").strip()
        product_id = (raw_row.get("product_id") or "").strip()
        supplier_id = (raw_row.get("supplier_id") or "").strip()
        order_date, order_date_error = parse_date(raw_row.get("order_date"), "order_date")
        promised_receipt_date, promised_error = parse_date(
            raw_row.get("promised_receipt_date"), "promised_receipt_date"
        )
        actual_receipt_date, actual_error = parse_optional_date(
            raw_row.get("actual_receipt_date"), "actual_receipt_date"
        )
        ordered_qty, ordered_error = parse_int(raw_row.get("ordered_qty"), "ordered_qty", minimum=1)
        received_qty, received_error = parse_optional_int(
            raw_row.get("received_qty"), "received_qty", minimum=0
        )
        status = (raw_row.get("status") or "").strip()
        status_error = (
            "status is missing" if not status else check_in_set(status, ALLOWED_STATUSES, "status")
        )

        errors = [
            e
            for e in (order_date_error, promised_error, actual_error, ordered_error, received_error, status_error)
            if e
        ]
        if not order_id:
            errors.append("order_id is missing")
        if not product_id:
            errors.append("product_id is missing")
        elif product_id not in known_product_ids:
            errors.append(f"unknown product_id {product_id!r} (not in clean.product)")
        if not supplier_id:
            errors.append("supplier_id is missing")
        elif supplier_id not in known_supplier_ids:
            errors.append(f"unknown supplier_id {supplier_id!r} (not in clean.supplier)")

        if errors:
            report.add(
                QualityIssue(
                    TABLE_NAME, IssueKind.REJECTED, "invalid_purchase_order_line", key, "; ".join(errors)
                )
            )
            continue

        clean_rows.append(
            {
                "order_id": order_id,
                "product_id": product_id,
                "supplier_id": supplier_id,
                "order_date": order_date,
                "promised_receipt_date": promised_receipt_date,
                "actual_receipt_date": actual_receipt_date,
                "ordered_qty": ordered_qty,
                "received_qty": received_qty,
                "status": status,
            }
        )

    report.rows_loaded[TABLE_NAME] = len(clean_rows)
    return clean_rows
