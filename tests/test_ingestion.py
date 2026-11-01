"""Tests for the P1.4 ingestion pipeline.

Project rule (docs/ARCHITECTURE.md §2): invalid records are reported, never
silently dropped or repaired. These tests check, table by table, that each
documented missing-data rule (docs/DATA_DICTIONARY.md) produces the right kind
of QualityIssue (REJECTED / FLAGGED / MISSING) - and, just as important, that a
legitimate value is never mistakenly flagged.
"""

from __future__ import annotations

from supply_planning.ingestion.product import validate_rows as validate_products
from supply_planning.ingestion.quality import IssueKind, QualityReport
from supply_planning.ingestion.validators import (
    check_in_set,
    parse_bool,
    parse_date,
    parse_int,
    parse_optional_int,
    parse_required_text,
)

# --- validators.py ----------------------------------------------------------


def test_parse_required_text_rejects_empty() -> None:
    value, error = parse_required_text("  ", "product_id")
    assert value is None
    assert error is not None


def test_parse_required_text_strips_whitespace() -> None:
    value, error = parse_required_text(" FOOT-01-42 ", "product_id")
    assert value == "FOOT-01-42"
    assert error is None


def test_parse_int_rejects_non_integer() -> None:
    value, error = parse_int("abc", "units_sold")
    assert value is None
    assert error is not None


def test_parse_int_enforces_minimum() -> None:
    value, error = parse_int("-1", "units_sold", minimum=0)
    assert value is None
    assert error is not None


def test_parse_optional_int_allows_missing() -> None:
    value, error = parse_optional_int("", "received_qty")
    assert value is None
    assert error is None  # missing is legitimate here, unlike parse_int alone


def test_parse_date_rejects_bad_format() -> None:
    value, error = parse_date("2026/03/02", "order_date")
    assert value is None
    assert error is not None


def test_parse_bool_accepts_python_str_repr() -> None:
    value, error = parse_bool("True", "was_stocked_out")
    assert value is True
    assert error is None


def test_parse_bool_rejects_garbage() -> None:
    value, error = parse_bool("maybe", "was_stocked_out")
    assert value is None
    assert error is not None


def test_check_in_set() -> None:
    assert check_in_set("FOOT", ("FOOT", "APPAREL"), "family") is None
    assert check_in_set("SHOES", ("FOOT", "APPAREL"), "family") is not None


# --- product.py --------------------------------------------------------------

_VALID_PRODUCT_ROW = {
    "product_id": "FOOT-01-42",
    "product_name": "Ridge Trail Shoe",
    "family": "FOOT",
    "size": "42",
    "unit_of_measure": "piece",
}


def test_valid_product_row_is_loaded_without_issues() -> None:
    report = QualityReport()
    rows = validate_products([_VALID_PRODUCT_ROW], report)
    assert rows == [_VALID_PRODUCT_ROW]
    assert report.issues == []
    assert report.rows_read["product"] == 1
    assert report.rows_loaded["product"] == 1


def test_unknown_family_is_rejected_not_defaulted() -> None:
    bad_row = {**_VALID_PRODUCT_ROW, "family": "SHOES"}
    report = QualityReport()
    rows = validate_products([bad_row], report)
    assert rows == []
    assert report.count_by_kind("product", IssueKind.REJECTED) == 1
    assert report.issues[0].reason_code == "invalid_product"


def test_missing_product_id_is_rejected() -> None:
    bad_row = {**_VALID_PRODUCT_ROW, "product_id": ""}
    report = QualityReport()
    rows = validate_products([bad_row], report)
    assert rows == []
    assert "product_id" in report.issues[0].detail


def test_foot_product_without_size_is_rejected() -> None:
    bad_row = {**_VALID_PRODUCT_ROW, "size": ""}
    report = QualityReport()
    rows = validate_products([bad_row], report)
    assert rows == []
    assert report.count_by_kind("product", IssueKind.REJECTED) == 1


def test_non_foot_product_with_size_is_rejected() -> None:
    bad_row = {
        "product_id": "APPAREL-001",
        "product_name": "Windshell Jacket 001",
        "family": "APPAREL",
        "size": "42",  # size must be NULL outside FOOT
        "unit_of_measure": "piece",
    }
    report = QualityReport()
    rows = validate_products([bad_row], report)
    assert rows == []
    assert report.count_by_kind("product", IssueKind.REJECTED) == 1


def test_duplicate_product_id_in_same_batch_is_rejected() -> None:
    report = QualityReport()
    rows = validate_products([_VALID_PRODUCT_ROW, _VALID_PRODUCT_ROW], report)
    assert rows == []  # both copies rejected, never pick a winner silently
    assert report.count_by_kind("product", IssueKind.REJECTED) == 2
    assert all(issue.reason_code == "duplicate_key" for issue in report.issues)


# --- calendar.py --------------------------------------------------------------

from supply_planning.ingestion.calendar import validate_rows as validate_calendar
from supply_planning.ingestion.supplier import validate_rows as validate_suppliers

_VALID_CALENDAR_ROW = {
    "calendar_date": "2026-03-02",
    "week_start_date": "2026-03-02",
    "iso_year": "2026",
    "iso_week_number": "10",
}


def test_valid_calendar_row_is_loaded() -> None:
    report = QualityReport()
    rows = validate_calendar([_VALID_CALENDAR_ROW], report)
    assert len(rows) == 1
    assert report.issues == []


def test_calendar_row_with_bad_date_is_rejected() -> None:
    bad_row = {**_VALID_CALENDAR_ROW, "calendar_date": "02/03/2026"}
    report = QualityReport()
    rows = validate_calendar([bad_row], report)
    assert rows == []
    assert report.count_by_kind("calendar", IssueKind.REJECTED) == 1


def test_calendar_row_with_week_number_54_is_rejected() -> None:
    bad_row = {**_VALID_CALENDAR_ROW, "iso_week_number": "54"}
    report = QualityReport()
    rows = validate_calendar([bad_row], report)
    assert rows == []


def test_duplicate_calendar_date_is_rejected() -> None:
    report = QualityReport()
    rows = validate_calendar([_VALID_CALENDAR_ROW, _VALID_CALENDAR_ROW], report)
    assert rows == []
    assert report.count_by_kind("calendar", IssueKind.REJECTED) == 2


# --- supplier.py ---------------------------------------------------------------

_VALID_SUPPLIER_ROW = {"supplier_id": "SUP-01", "supplier_name": "Pyrenees Textile Co."}


def test_valid_supplier_row_is_loaded() -> None:
    report = QualityReport()
    rows = validate_suppliers([_VALID_SUPPLIER_ROW], report)
    assert rows == [_VALID_SUPPLIER_ROW]
    assert report.issues == []


def test_supplier_row_missing_name_is_rejected() -> None:
    bad_row = {**_VALID_SUPPLIER_ROW, "supplier_name": ""}
    report = QualityReport()
    rows = validate_suppliers([bad_row], report)
    assert rows == []
    assert report.count_by_kind("supplier", IssueKind.REJECTED) == 1


# --- demand_actual.py ----------------------------------------------------------

from datetime import date as _date

from supply_planning.ingestion.demand_actual import validate_rows as validate_demand

_KNOWN_PRODUCTS = {"APPAREL-001", "APPAREL-002"}
_KNOWN_WEEKS = {_date(2026, 3, 2), _date(2026, 3, 9), _date(2026, 3, 16)}


def _demand_row(product_id: str, week: str, units_sold: str = "10", was_stocked_out: str = "False") -> dict:
    return {
        "product_id": product_id,
        "week_start_date": week,
        "units_sold": units_sold,
        "was_stocked_out": was_stocked_out,
    }


def test_valid_demand_rows_are_loaded_without_issues() -> None:
    rows = [_demand_row("APPAREL-001", w) for w in ("2026-03-02", "2026-03-09", "2026-03-16")]
    report = QualityReport()
    clean_rows = validate_demand(rows, report, known_product_ids=_KNOWN_PRODUCTS, known_calendar_dates=_KNOWN_WEEKS)
    assert len(clean_rows) == 3
    assert report.issues == []


def test_unknown_product_id_is_rejected() -> None:
    rows = [_demand_row("GHOST-999", "2026-03-02")]
    report = QualityReport()
    clean_rows = validate_demand(rows, report, known_product_ids=_KNOWN_PRODUCTS, known_calendar_dates=_KNOWN_WEEKS)
    assert clean_rows == []
    assert report.count_by_kind("demand_actual", IssueKind.REJECTED) == 1


def test_unknown_week_is_rejected() -> None:
    rows = [_demand_row("APPAREL-001", "2099-01-05")]
    report = QualityReport()
    clean_rows = validate_demand(rows, report, known_product_ids=_KNOWN_PRODUCTS, known_calendar_dates=_KNOWN_WEEKS)
    assert clean_rows == []
    assert report.count_by_kind("demand_actual", IssueKind.REJECTED) == 1


def test_negative_units_sold_is_rejected() -> None:
    rows = [_demand_row("APPAREL-001", "2026-03-02", units_sold="-5")]
    report = QualityReport()
    clean_rows = validate_demand(rows, report, known_product_ids=_KNOWN_PRODUCTS, known_calendar_dates=_KNOWN_WEEKS)
    assert clean_rows == []


def test_a_true_zero_demand_week_is_loaded_and_never_flagged() -> None:
    """The P1.3 edge case: a genuine 3-week run of zero demand must load cleanly
    and must NOT appear in the quality report under any reason code."""
    rows = [_demand_row("APPAREL-002", w, units_sold="0") for w in ("2026-03-02", "2026-03-09", "2026-03-16")]
    report = QualityReport()
    clean_rows = validate_demand(rows, report, known_product_ids=_KNOWN_PRODUCTS, known_calendar_dates=_KNOWN_WEEKS)
    assert len(clean_rows) == 3
    assert all(row["units_sold"] == 0 for row in clean_rows)
    assert report.issues == []


def test_missing_sku_week_is_detected_as_an_absence_not_a_rejection() -> None:
    """The P1.3 edge case: APPAREL-001 is missing its last week's row entirely."""
    rows = [
        _demand_row("APPAREL-001", "2026-03-02"),
        _demand_row("APPAREL-001", "2026-03-09"),
        # APPAREL-001 / 2026-03-16 deliberately absent
        _demand_row("APPAREL-002", "2026-03-02"),
        _demand_row("APPAREL-002", "2026-03-09"),
        _demand_row("APPAREL-002", "2026-03-16"),
    ]
    report = QualityReport()
    clean_rows = validate_demand(rows, report, known_product_ids=_KNOWN_PRODUCTS, known_calendar_dates=_KNOWN_WEEKS)
    assert len(clean_rows) == 5  # every valid row IS loaded - nothing was rejected
    missing_issues = [i for i in report.issues if i.reason_code == "missing_sku_week"]
    assert len(missing_issues) == 1
    assert missing_issues[0].key == ("APPAREL-001", "2026-03-16")


def test_duplicate_demand_key_is_rejected() -> None:
    rows = [_demand_row("APPAREL-001", "2026-03-02"), _demand_row("APPAREL-001", "2026-03-02")]
    report = QualityReport()
    clean_rows = validate_demand(rows, report, known_product_ids=_KNOWN_PRODUCTS, known_calendar_dates=_KNOWN_WEEKS)
    assert clean_rows == []
    assert report.count_by_kind("demand_actual", IssueKind.REJECTED) == 2


# --- inventory_snapshot.py ------------------------------------------------------

from supply_planning.ingestion.inventory_snapshot import validate_rows as validate_inventory


def _inventory_row(product_id: str, snapshot_date: str, on_hand: str = "50", allocated: str = "10") -> dict:
    return {
        "product_id": product_id,
        "site_id": "WH-01",
        "snapshot_date": snapshot_date,
        "on_hand_qty": on_hand,
        "allocated_qty": allocated,
    }


def test_valid_inventory_row_is_loaded_without_issues() -> None:
    rows = [_inventory_row("APPAREL-001", "2026-03-02")]
    report = QualityReport()
    clean_rows = validate_inventory(rows, report, known_product_ids=_KNOWN_PRODUCTS, known_calendar_dates=_KNOWN_WEEKS)
    assert len(clean_rows) == 1
    assert report.issues == []


def test_negative_available_stock_is_flagged_but_still_loaded() -> None:
    """The P1.3 edge case: allocated_qty > on_hand_qty must load (it's a real,
    valid fact), and must also appear in the quality report as a warning."""
    rows = [_inventory_row("APPAREL-003".replace("003", "001"), "2026-03-02", on_hand="10", allocated="15")]
    report = QualityReport()
    clean_rows = validate_inventory(rows, report, known_product_ids=_KNOWN_PRODUCTS, known_calendar_dates=_KNOWN_WEEKS)
    assert len(clean_rows) == 1  # loaded, not rejected
    flagged = [i for i in report.issues if i.reason_code == "negative_available_stock"]
    assert len(flagged) == 1
    assert flagged[0].kind == IssueKind.FLAGGED


def test_inventory_row_with_unknown_product_is_rejected() -> None:
    rows = [_inventory_row("GHOST-999", "2026-03-02")]
    report = QualityReport()
    clean_rows = validate_inventory(rows, report, known_product_ids=_KNOWN_PRODUCTS, known_calendar_dates=_KNOWN_WEEKS)
    assert clean_rows == []
    assert report.count_by_kind("inventory_snapshot", IssueKind.REJECTED) == 1


def test_inventory_row_with_negative_on_hand_qty_is_rejected() -> None:
    rows = [_inventory_row("APPAREL-001", "2026-03-02", on_hand="-5")]
    report = QualityReport()
    clean_rows = validate_inventory(rows, report, known_product_ids=_KNOWN_PRODUCTS, known_calendar_dates=_KNOWN_WEEKS)
    assert clean_rows == []


# --- purchase_order_line.py ------------------------------------------------------

from supply_planning.ingestion.purchase_order_line import validate_rows as validate_purchase_orders

_KNOWN_SUPPLIERS = {"SUP-01"}


def _po_row(
    order_id: str,
    product_id: str = "APPAREL-001",
    *,
    promised: str = "2026-05-01",
    status: str = "received",
    actual: str = "2026-05-01",
    received_qty: str = "40",
    ordered_qty: str = "40",
) -> dict:
    return {
        "order_id": order_id,
        "product_id": product_id,
        "supplier_id": "SUP-01",
        "order_date": "2026-03-30",
        "promised_receipt_date": promised,
        "actual_receipt_date": actual,
        "ordered_qty": ordered_qty,
        "received_qty": received_qty,
        "status": status,
    }


def test_valid_purchase_order_line_is_loaded() -> None:
    report = QualityReport()
    rows = validate_purchase_orders(
        [_po_row("PO-00001")], report, known_product_ids=_KNOWN_PRODUCTS, known_supplier_ids=_KNOWN_SUPPLIERS
    )
    assert len(rows) == 1
    assert report.issues == []


def test_missing_promised_date_is_rejected_on_received_status() -> None:
    report = QualityReport()
    rows = validate_purchase_orders(
        [_po_row("PO-00001", promised="")],
        report,
        known_product_ids=_KNOWN_PRODUCTS,
        known_supplier_ids=_KNOWN_SUPPLIERS,
    )
    assert rows == []
    assert report.count_by_kind("purchase_order_line", IssueKind.REJECTED) == 1


def test_missing_promised_date_is_rejected_even_on_draft_status() -> None:
    """clean.purchase_order_line requires promised_receipt_date regardless of
    status - the NOT NULL constraint has no exception for 'draft'."""
    report = QualityReport()
    rows = validate_purchase_orders(
        [_po_row("PO-00002", promised="", status="draft", actual="", received_qty="")],
        report,
        known_product_ids=_KNOWN_PRODUCTS,
        known_supplier_ids=_KNOWN_SUPPLIERS,
    )
    assert rows == []


def test_received_qty_can_be_null_for_an_open_order() -> None:
    report = QualityReport()
    rows = validate_purchase_orders(
        [_po_row("PO-00003", status="confirmed", actual="", received_qty="")],
        report,
        known_product_ids=_KNOWN_PRODUCTS,
        known_supplier_ids=_KNOWN_SUPPLIERS,
    )
    assert len(rows) == 1
    assert rows[0]["received_qty"] is None
    assert report.issues == []


def test_invalid_status_is_rejected() -> None:
    report = QualityReport()
    rows = validate_purchase_orders(
        [_po_row("PO-00004", status="shipped")],
        report,
        known_product_ids=_KNOWN_PRODUCTS,
        known_supplier_ids=_KNOWN_SUPPLIERS,
    )
    assert rows == []


def test_unknown_supplier_is_rejected() -> None:
    row = {**_po_row("PO-00005"), "supplier_id": "SUP-99"}
    report = QualityReport()
    rows = validate_purchase_orders(
        [row], report, known_product_ids=_KNOWN_PRODUCTS, known_supplier_ids=_KNOWN_SUPPLIERS
    )
    assert rows == []


def test_zero_ordered_qty_is_rejected() -> None:
    report = QualityReport()
    rows = validate_purchase_orders(
        [_po_row("PO-00006", ordered_qty="0")],
        report,
        known_product_ids=_KNOWN_PRODUCTS,
        known_supplier_ids=_KNOWN_SUPPLIERS,
    )
    assert rows == []


def test_duplicate_order_product_key_is_rejected() -> None:
    report = QualityReport()
    rows = validate_purchase_orders(
        [_po_row("PO-00007"), _po_row("PO-00007")],
        report,
        known_product_ids=_KNOWN_PRODUCTS,
        known_supplier_ids=_KNOWN_SUPPLIERS,
    )
    assert rows == []
    assert report.count_by_kind("purchase_order_line", IssueKind.REJECTED) == 2


# --- capacity.py -----------------------------------------------------------------

from supply_planning.ingestion.capacity import validate_rows as validate_capacity


def _capacity_row(family: str = "FOOT", week: str = "2026-03-02", available: str = "3150", planned: str = "2500") -> dict:
    return {
        "site_id": "WH-01",
        "family": family,
        "week_start_date": week,
        "available_capacity_units": available,
        "planned_load_units": planned,
    }


def test_valid_capacity_row_is_loaded_without_issues() -> None:
    report = QualityReport()
    rows = validate_capacity([_capacity_row()], report, known_calendar_dates=_KNOWN_WEEKS)
    assert len(rows) == 1
    assert report.issues == []


def test_capacity_overload_is_flagged_but_still_loaded() -> None:
    report = QualityReport()
    rows = validate_capacity(
        [_capacity_row(available="3000", planned="3900")], report, known_calendar_dates=_KNOWN_WEEKS
    )
    assert len(rows) == 1  # loaded, not rejected
    flagged = [i for i in report.issues if i.reason_code == "capacity_overload"]
    assert len(flagged) == 1
    assert flagged[0].kind == IssueKind.FLAGGED


def test_capacity_row_with_invalid_family_is_rejected() -> None:
    report = QualityReport()
    rows = validate_capacity([_capacity_row(family="SHOES")], report, known_calendar_dates=_KNOWN_WEEKS)
    assert rows == []


def test_capacity_row_with_unknown_week_is_rejected() -> None:
    report = QualityReport()
    rows = validate_capacity([_capacity_row(week="2099-01-05")], report, known_calendar_dates=_KNOWN_WEEKS)
    assert rows == []
