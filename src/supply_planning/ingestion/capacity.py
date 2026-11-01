"""`capacity` (`fct_capacity`) validation: `raw.capacity` -> `clean.capacity`
(docs/DATA_DICTIONARY.md §7).

`planned_load_units > available_capacity_units` is **not** rejected and **not**
capped: `docs/BUSINESS_RULES.md` §4.3 is explicit that overload "is exactly the
information to surface". The row is loaded as-is, and also FLAGGED in the
quality report as `capacity_overload`, the same pattern as inventory's
negative-available-stock case.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from .quality import IssueKind, QualityIssue, QualityReport
from .validators import check_in_set, parse_date, parse_int, parse_required_text

TABLE_NAME = "capacity"
ALLOWED_FAMILIES = ("FOOT", "APPAREL", "PACK", "NUTRI")


def _find_duplicate_keys(raw_rows: list[dict[str, str]]) -> set[tuple[str, ...]]:
    seen: set[tuple[str, ...]] = set()
    duplicates: set[tuple[str, ...]] = set()
    for raw_row in raw_rows:
        key = (
            raw_row.get("site_id") or "",
            raw_row.get("family") or "",
            raw_row.get("week_start_date") or "",
        )
        if key in seen:
            duplicates.add(key)
        seen.add(key)
    return duplicates


def validate_rows(
    raw_rows: list[dict[str, str]],
    report: QualityReport,
    *,
    known_calendar_dates: set[date],
) -> list[dict[str, Any]]:
    report.rows_read[TABLE_NAME] = report.rows_read.get(TABLE_NAME, 0) + len(raw_rows)
    duplicate_keys = _find_duplicate_keys(raw_rows)

    clean_rows: list[dict[str, Any]] = []
    for raw_row in raw_rows:
        key = (
            raw_row.get("site_id") or "",
            raw_row.get("family") or "",
            raw_row.get("week_start_date") or "",
        )

        if key in duplicate_keys:
            report.add(
                QualityIssue(
                    TABLE_NAME, IssueKind.REJECTED, "duplicate_key", key,
                    f"{key} appears more than once in this batch",
                )
            )
            continue

        site_id, site_error = parse_required_text(raw_row.get("site_id"), "site_id")
        family = (raw_row.get("family") or "").strip()
        family_error = "family is missing" if not family else check_in_set(
            family, ALLOWED_FAMILIES, "family"
        )
        week_start_date, date_error = parse_date(raw_row.get("week_start_date"), "week_start_date")
        available_capacity_units, available_error = parse_int(
            raw_row.get("available_capacity_units"), "available_capacity_units", minimum=0
        )
        planned_load_units, planned_error = parse_int(
            raw_row.get("planned_load_units"), "planned_load_units", minimum=0
        )

        errors = [e for e in (site_error, family_error, date_error, available_error, planned_error) if e]
        if week_start_date is not None and week_start_date not in known_calendar_dates:
            errors.append(f"unknown week_start_date {week_start_date} (not in clean.calendar)")

        if errors:
            report.add(
                QualityIssue(TABLE_NAME, IssueKind.REJECTED, "invalid_capacity", key, "; ".join(errors))
            )
            continue

        if planned_load_units > available_capacity_units:
            report.add(
                QualityIssue(
                    TABLE_NAME,
                    IssueKind.FLAGGED,
                    "capacity_overload",
                    key,
                    f"planned_load_units ({planned_load_units}) > "
                    f"available_capacity_units ({available_capacity_units})",
                )
            )

        clean_rows.append(
            {
                "site_id": site_id,
                "family": family,
                "week_start_date": week_start_date,
                "available_capacity_units": available_capacity_units,
                "planned_load_units": planned_load_units,
            }
        )

    report.rows_loaded[TABLE_NAME] = len(clean_rows)
    return clean_rows
