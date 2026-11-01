"""dim_calendar generator (docs/DATA_DICTIONARY.md §2).

Purely computed from ISO 8601 week rules - no randomness, no seed needed, because
the calendar is a derived dimension, never sourced from anywhere
(docs/ARCHITECTURE.md §4).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class CalendarRow:
    calendar_date: date
    week_start_date: date
    iso_year: int
    iso_week_number: int


def generate_calendar(start_date: date, end_date: date) -> list[CalendarRow]:
    """Generate one row per calendar date, covering whole ISO weeks.

    `start_date` is pulled back to its own Monday and `end_date` pushed forward to
    its own Sunday: every weekly fact's `week_start_date` must find a matching row
    here, so the table must never stop in the middle of a week.
    """
    if end_date < start_date:
        raise ValueError(f"end_date {end_date} is before start_date {start_date}.")

    first_monday = start_date - timedelta(days=start_date.isoweekday() - 1)
    last_sunday = end_date + timedelta(days=7 - end_date.isoweekday())

    rows: list[CalendarRow] = []
    current = first_monday
    while current <= last_sunday:
        iso_year, iso_week_number, _ = current.isocalendar()
        week_start = current - timedelta(days=current.isoweekday() - 1)
        rows.append(
            CalendarRow(
                calendar_date=current,
                week_start_date=week_start,
                iso_year=iso_year,
                iso_week_number=iso_week_number,
            )
        )
        current += timedelta(days=1)
    return rows
