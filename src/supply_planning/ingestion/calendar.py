"""`calendar` (`dim_calendar`) validation: `raw.calendar` -> `clean.calendar`
(docs/DATA_DICTIONARY.md §2).

A root dimension with no foreign key - the only things to check are "does every
field parse" and "no duplicate `calendar_date`". By construction (generated in
Python, never sourced externally, docs/ARCHITECTURE.md §4) it should never be
missing or malformed, but ingestion does not get to *assume* that about any
source, including its own generator - it checks and reports like every table.
"""

from __future__ import annotations

from typing import Any

from .quality import IssueKind, QualityIssue, QualityReport
from .validators import parse_date, parse_int

TABLE_NAME = "calendar"


def _find_duplicate_keys(raw_rows: list[dict[str, str]]) -> set[tuple[str, ...]]:
    seen: set[tuple[str, ...]] = set()
    duplicates: set[tuple[str, ...]] = set()
    for raw_row in raw_rows:
        key = (raw_row.get("calendar_date") or "",)
        if key in seen:
            duplicates.add(key)
        seen.add(key)
    return duplicates


def validate_rows(raw_rows: list[dict[str, str]], report: QualityReport) -> list[dict[str, Any]]:
    report.rows_read[TABLE_NAME] = report.rows_read.get(TABLE_NAME, 0) + len(raw_rows)
    duplicate_keys = _find_duplicate_keys(raw_rows)

    clean_rows: list[dict[str, Any]] = []
    for raw_row in raw_rows:
        key = (raw_row.get("calendar_date") or "",)

        if key in duplicate_keys:
            report.add(
                QualityIssue(
                    TABLE_NAME, IssueKind.REJECTED, "duplicate_key", key,
                    f"calendar_date {raw_row.get('calendar_date')!r} appears more than once",
                )
            )
            continue

        calendar_date, date_error = parse_date(raw_row.get("calendar_date"), "calendar_date")
        week_start_date, week_error = parse_date(raw_row.get("week_start_date"), "week_start_date")
        iso_year, year_error = parse_int(raw_row.get("iso_year"), "iso_year")
        iso_week_number, week_number_error = parse_int(
            raw_row.get("iso_week_number"), "iso_week_number", minimum=1
        )

        errors = [e for e in (date_error, week_error, year_error, week_number_error) if e]
        if iso_week_number is not None and iso_week_number > 53:
            errors.append(f"iso_week_number must be <= 53, got {iso_week_number}")

        if errors:
            report.add(
                QualityIssue(TABLE_NAME, IssueKind.REJECTED, "invalid_calendar_row", key, "; ".join(errors))
            )
            continue

        clean_rows.append(
            {
                "calendar_date": calendar_date,
                "week_start_date": week_start_date,
                "iso_year": iso_year,
                "iso_week_number": iso_week_number,
            }
        )

    report.rows_loaded[TABLE_NAME] = len(clean_rows)
    return clean_rows
