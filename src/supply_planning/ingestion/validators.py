"""Small, explicit parsing helpers shared by every table's clean-loading step.

Every raw column is TEXT (`sql/002_raw_tables.sql`) - these functions turn a raw
string into either a typed Python value or an explicit error message. None of
them raise: a parsing failure is exactly what the project rule requires to be
*reported*, not an exception that aborts the whole batch.

Convention: every parser returns `(value, error)`. `error is None` means
success. Callers accumulate the error as a `QualityIssue` instead of crashing.
"""

from __future__ import annotations

from datetime import date, datetime


def parse_required_text(raw_value: str | None, field_name: str) -> tuple[str | None, str | None]:
    if raw_value is None or raw_value.strip() == "":
        return None, f"{field_name} is missing"
    return raw_value.strip(), None


def parse_optional_text(raw_value: str | None) -> str | None:
    """A field allowed to be legitimately absent (e.g. `dim_product.size`)."""
    if raw_value is None or raw_value.strip() == "":
        return None
    return raw_value.strip()


def parse_int(
    raw_value: str | None, field_name: str, *, minimum: int | None = None
) -> tuple[int | None, str | None]:
    if raw_value is None or raw_value.strip() == "":
        return None, f"{field_name} is missing"
    try:
        value = int(raw_value.strip())
    except ValueError:
        return None, f"{field_name} is not an integer: {raw_value!r}"
    if minimum is not None and value < minimum:
        return None, f"{field_name} must be >= {minimum}, got {value}"
    return value, None


def parse_optional_int(
    raw_value: str | None, field_name: str, *, minimum: int | None = None
) -> tuple[int | None, str | None]:
    """A field allowed to be legitimately NULL (e.g. `received_qty` while open —
    NULL means "outcome unknown", distinct from 0, docs/DATA_DICTIONARY.md §6)."""
    if raw_value is None or raw_value.strip() == "":
        return None, None
    return parse_int(raw_value, field_name, minimum=minimum)


def parse_date(raw_value: str | None, field_name: str) -> tuple[date | None, str | None]:
    if raw_value is None or raw_value.strip() == "":
        return None, f"{field_name} is missing"
    try:
        return datetime.strptime(raw_value.strip(), "%Y-%m-%d").date(), None
    except ValueError:
        return None, f"{field_name} is not a date (YYYY-MM-DD): {raw_value!r}"


def parse_optional_date(raw_value: str | None, field_name: str) -> tuple[date | None, str | None]:
    if raw_value is None or raw_value.strip() == "":
        return None, None
    return parse_date(raw_value, field_name)


def parse_bool(raw_value: str | None, field_name: str) -> tuple[bool | None, str | None]:
    if raw_value is None or raw_value.strip() == "":
        return None, f"{field_name} is missing"
    normalised = raw_value.strip().lower()
    if normalised in ("true", "1"):
        return True, None
    if normalised in ("false", "0"):
        return False, None
    return None, f"{field_name} is not a boolean: {raw_value!r}"


def check_in_set(value: str, allowed: tuple[str, ...], field_name: str) -> str | None:
    if value not in allowed:
        return f"{field_name} {value!r} is not one of {allowed}"
    return None
