"""`demand_actual` (`fct_demand_actual`) validation: `raw.demand_actual` ->
`clean.demand_actual` (docs/DATA_DICTIONARY.md §4).

Two mechanisms, not one:
  - REJECTED rows: unknown `product_id`/`week_start_date` (foreign keys that do
    not exist in the already-loaded dimensions), a non-numeric or negative
    `units_sold`, an unparseable `was_stocked_out`, or a duplicate key.
  - MISSING (no row to reject): "every `product_id` active during a given
    `week_start_date` must have a row, even `units_sold = 0`"
    (docs/DATA_DICTIONARY.md §4). Checked *after* loading, by comparing the
    loaded keys against the full product x week grid this batch implies - a
    genuine zero-demand row (a legitimate, loaded fact) must never be confused
    with this case.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from .quality import IssueKind, QualityIssue, QualityReport
from .validators import parse_bool, parse_date, parse_int

TABLE_NAME = "demand_actual"


def _find_duplicate_keys(raw_rows: list[dict[str, str]]) -> set[tuple[str, ...]]:
    seen: set[tuple[str, ...]] = set()
    duplicates: set[tuple[str, ...]] = set()
    for raw_row in raw_rows:
        key = (raw_row.get("product_id") or "", raw_row.get("week_start_date") or "")
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
        key = (raw_row.get("product_id") or "", raw_row.get("week_start_date") or "")

        if key in duplicate_keys:
            report.add(
                QualityIssue(
                    TABLE_NAME, IssueKind.REJECTED, "duplicate_key", key,
                    f"{key} appears more than once in this batch",
                )
            )
            continue

        product_id = (raw_row.get("product_id") or "").strip()
        week_start_date, date_error = parse_date(raw_row.get("week_start_date"), "week_start_date")
        units_sold, units_error = parse_int(raw_row.get("units_sold"), "units_sold", minimum=0)
        was_stocked_out, bool_error = parse_bool(raw_row.get("was_stocked_out"), "was_stocked_out")

        errors = [e for e in (date_error, units_error, bool_error) if e]
        if not product_id:
            errors.append("product_id is missing")
        elif product_id not in known_product_ids:
            errors.append(f"unknown product_id {product_id!r} (not in clean.product)")
        if week_start_date is not None and week_start_date not in known_calendar_dates:
            errors.append(f"unknown week_start_date {week_start_date} (not in clean.calendar)")

        if errors:
            report.add(
                QualityIssue(TABLE_NAME, IssueKind.REJECTED, "invalid_demand_actual", key, "; ".join(errors))
            )
            continue

        clean_rows.append(
            {
                "product_id": product_id,
                "week_start_date": week_start_date,
                "units_sold": units_sold,
                "was_stocked_out": was_stocked_out,
            }
        )

    report.rows_loaded[TABLE_NAME] = len(clean_rows)
    _report_missing_sku_weeks(clean_rows, report)
    return clean_rows


def _report_missing_sku_weeks(clean_rows: list[dict[str, Any]], report: QualityReport) -> None:
    """docs/DATA_DICTIONARY.md §4: every product active in this batch must have a
    row for every week this batch covers - a gap is a data-quality defect, never
    an implicit zero (docs/data/sample edge case: APPAREL-001 / 2026-09-21)."""
    present_products = {row["product_id"] for row in clean_rows}
    present_weeks = {row["week_start_date"] for row in clean_rows}
    present_keys = {(row["product_id"], row["week_start_date"]) for row in clean_rows}

    for product_id in sorted(present_products):
        for week_start_date in sorted(present_weeks):
            key = (product_id, str(week_start_date))
            if (product_id, week_start_date) not in present_keys:
                report.add(
                    QualityIssue(
                        TABLE_NAME,
                        IssueKind.MISSING,
                        "missing_sku_week",
                        key,
                        f"no demand_actual row for {product_id} / {week_start_date}",
                    )
                )
