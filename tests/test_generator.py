"""Tests for the P1.3 synthetic-data generator.

Project rule (docs/ARCHITECTURE.md §5): generation is seeded and must be
reproducible. These tests check that property directly, plus the shape invariants
each table's grain depends on (docs/DATA_DICTIONARY.md).
"""

from __future__ import annotations

from datetime import date, timedelta

from supply_planning.generator.calendar import generate_calendar
from supply_planning.generator.demand import generate_demand
from supply_planning.generator.product import FOOT_SIZES, generate_products
from supply_planning.generator.supplier import generate_suppliers

_TEN_WEEKS = [date(2024, 1, 1) + timedelta(weeks=i) for i in range(10)]


def test_calendar_covers_whole_iso_weeks() -> None:
    rows = generate_calendar(date(2024, 1, 3), date(2024, 1, 10))  # Wed -> Wed
    assert rows[0].calendar_date == date(2024, 1, 1)  # pulled back to the Monday
    assert rows[-1].calendar_date == date(2024, 1, 14)  # pushed forward to the Sunday
    assert len(rows) == 14  # two full ISO weeks


def test_calendar_week_start_date_is_the_monday() -> None:
    rows = generate_calendar(date(2024, 1, 1), date(2024, 1, 7))
    assert {row.week_start_date for row in rows} == {date(2024, 1, 1)}


def test_calendar_rejects_end_before_start() -> None:
    try:
        generate_calendar(date(2024, 1, 10), date(2024, 1, 1))
    except ValueError:
        return
    raise AssertionError("expected a ValueError when end_date < start_date")


def test_generate_products_is_deterministic() -> None:
    first_run = generate_products(seed=42)
    second_run = generate_products(seed=42)
    assert first_run == second_run


def test_generate_products_different_seed_changes_order() -> None:
    first_run = generate_products(seed=1)
    second_run = generate_products(seed=2)
    assert [row.product_id for row in first_run] != [row.product_id for row in second_run]


def test_generate_products_matches_asm01_total() -> None:
    rows = generate_products(seed=1)
    assert len(rows) == 120  # ASM-01: ~120 active SKUs


def test_foot_products_have_size_every_other_family_does_not() -> None:
    rows = generate_products(seed=1)
    for row in rows:
        if row.family == "FOOT":
            assert row.size is not None and int(row.size) in FOOT_SIZES
        else:
            assert row.size is None


def test_generate_suppliers_is_fixed_and_nonempty() -> None:
    first_run = generate_suppliers()
    second_run = generate_suppliers()
    assert first_run == second_run
    assert len(first_run) > 0


def test_generate_demand_is_deterministic() -> None:
    products = generate_products(seed=1)
    rows_a, edge_a = generate_demand(products, _TEN_WEEKS, seed=7)
    rows_b, edge_b = generate_demand(products, _TEN_WEEKS, seed=7)
    assert rows_a == rows_b
    assert edge_a == edge_b


def test_generate_demand_has_missing_sku_week_edge_case() -> None:
    products = generate_products(seed=1)
    rows, edge_cases = generate_demand(products, _TEN_WEEKS, seed=7)

    present = {(row.product_id, row.week_start_date) for row in rows}
    assert edge_cases.missing_sku_week not in present
    # every other (product, week) combination must be present exactly once
    assert len(rows) == len(products) * len(_TEN_WEEKS) - 1


def test_generate_demand_zero_run_is_not_flagged_as_stockout() -> None:
    products = generate_products(seed=1)
    rows, edge_cases = generate_demand(products, _TEN_WEEKS, seed=7)

    zero_product, zero_weeks = edge_cases.zero_demand_run
    for row in rows:
        if row.product_id == zero_product and row.week_start_date in zero_weeks:
            assert row.units_sold == 0
            assert row.was_stocked_out is False


def test_generate_demand_units_sold_never_negative() -> None:
    products = generate_products(seed=3)
    weeks = [date(2024, 1, 1) + timedelta(weeks=i) for i in range(20)]
    rows, _ = generate_demand(products, weeks, seed=11)
    assert all(row.units_sold >= 0 for row in rows)


def test_generate_inventory_is_deterministic() -> None:
    from supply_planning.generator.inventory import generate_inventory_snapshots

    products = generate_products(seed=1)
    rows_a, edge_a = generate_inventory_snapshots(products, _TEN_WEEKS, seed=5)
    rows_b, edge_b = generate_inventory_snapshots(products, _TEN_WEEKS, seed=5)
    assert rows_a == rows_b
    assert edge_a == edge_b


def test_generate_inventory_has_negative_available_stock_case() -> None:
    from supply_planning.generator.inventory import generate_inventory_snapshots

    products = generate_products(seed=1)
    rows, edge_cases = generate_inventory_snapshots(products, _TEN_WEEKS, seed=5)

    product_id, snapshot_date = edge_cases.negative_available_stock
    matching = [
        row for row in rows if row.product_id == product_id and row.snapshot_date == snapshot_date
    ]
    assert len(matching) == 1
    assert matching[0].allocated_qty > matching[0].on_hand_qty


def test_generate_inventory_quantities_never_negative() -> None:
    from supply_planning.generator.inventory import generate_inventory_snapshots

    products = generate_products(seed=2)
    rows, _ = generate_inventory_snapshots(products, _TEN_WEEKS, seed=9)
    assert all(row.on_hand_qty >= 0 and row.allocated_qty >= 0 for row in rows)


def test_generate_purchase_orders_is_deterministic() -> None:
    from supply_planning.generator.purchase_order import generate_purchase_order_lines

    products = generate_products(seed=1)
    rows_a, edge_a = generate_purchase_order_lines(products, _TEN_WEEKS, seed=13)
    rows_b, edge_b = generate_purchase_order_lines(products, _TEN_WEEKS, seed=13)
    assert rows_a == rows_b
    assert edge_a == edge_b


def test_generate_purchase_orders_covers_every_status() -> None:
    from supply_planning.generator.purchase_order import generate_purchase_order_lines

    products = generate_products(seed=1)
    rows, _ = generate_purchase_order_lines(products, _TEN_WEEKS, seed=13)
    statuses = {row.status for row in rows}
    assert statuses == {
        "draft",
        "confirmed",
        "partially_received",
        "received",
        "cancelled_by_alpiflow",
        "cancelled_by_supplier",
    }


def test_generate_purchase_orders_otif_outcomes_present() -> None:
    from supply_planning.generator.purchase_order import generate_purchase_order_lines

    products = generate_products(seed=1)
    rows, _ = generate_purchase_order_lines(products, _TEN_WEEKS, seed=13)

    received_lines = [row for row in rows if row.status == "received"]
    on_time = [r for r in received_lines if r.actual_receipt_date == r.promised_receipt_date]
    late = [
        r
        for r in received_lines
        if r.promised_receipt_date and r.actual_receipt_date
        and r.actual_receipt_date > r.promised_receipt_date
    ]
    early = [
        r
        for r in received_lines
        if r.promised_receipt_date and r.actual_receipt_date
        and r.actual_receipt_date < r.promised_receipt_date
    ]
    assert on_time and late and early  # all three OTIF outcomes exist


def test_generate_purchase_orders_has_missing_promised_date_case() -> None:
    from supply_planning.generator.purchase_order import generate_purchase_order_lines

    products = generate_products(seed=1)
    rows, edge_cases = generate_purchase_order_lines(products, _TEN_WEEKS, seed=13)

    matching = [row for row in rows if row.order_id == edge_cases.missing_promised_date]
    assert len(matching) == 1
    assert matching[0].promised_receipt_date is None


def test_generate_purchase_orders_ordered_qty_always_positive() -> None:
    from supply_planning.generator.purchase_order import generate_purchase_order_lines

    products = generate_products(seed=2)
    rows, _ = generate_purchase_order_lines(products, _TEN_WEEKS, seed=4)
    assert all(row.ordered_qty > 0 for row in rows)


def test_generate_capacity_is_deterministic() -> None:
    from supply_planning.generator.capacity import generate_capacity

    rows_a, edge_a = generate_capacity(_TEN_WEEKS, seed=21)
    rows_b, edge_b = generate_capacity(_TEN_WEEKS, seed=21)
    assert rows_a == rows_b
    assert edge_a == edge_b


def test_generate_capacity_has_one_overloaded_week() -> None:
    from supply_planning.generator.capacity import generate_capacity

    rows, edge_cases = generate_capacity(_TEN_WEEKS, seed=21)
    site_id, family, week_start_date = edge_cases.overload
    matching = [
        row
        for row in rows
        if row.site_id == site_id and row.family == family and row.week_start_date == week_start_date
    ]
    assert len(matching) == 1
    assert matching[0].planned_load_units > matching[0].available_capacity_units


def test_generate_capacity_shares_sum_to_total() -> None:
    from supply_planning.generator.assumptions import DEFAULT_ASSUMPTIONS
    from supply_planning.generator.capacity import generate_capacity

    rows, _ = generate_capacity(_TEN_WEEKS, seed=21)
    first_week = _TEN_WEEKS[0]
    total_available = sum(row.available_capacity_units for row in rows if row.week_start_date == first_week)
    assert total_available == DEFAULT_ASSUMPTIONS.total_capacity_units_per_week


def test_generate_all_is_deterministic() -> None:
    from supply_planning.generator.run import generate_all

    dataset_a = generate_all(seed=99, start_date=date(2026, 1, 5), end_date=date(2026, 4, 5))
    dataset_b = generate_all(seed=99, start_date=date(2026, 1, 5), end_date=date(2026, 4, 5))
    assert dataset_a == dataset_b


def test_write_raw_csvs_produces_one_file_per_table_with_metadata_columns(tmp_path) -> None:
    from supply_planning.generator.run import generate_all, write_raw_csvs

    dataset = generate_all(seed=99, start_date=date(2026, 1, 5), end_date=date(2026, 4, 5))
    write_raw_csvs(dataset, tmp_path, load_id="test-load")

    expected_files = {
        "product.csv",
        "calendar.csv",
        "supplier.csv",
        "demand_actual.csv",
        "inventory_snapshot.csv",
        "purchase_order_line.csv",
        "capacity.csv",
    }
    assert {p.name for p in tmp_path.iterdir()} == expected_files

    import csv as csv_module

    with (tmp_path / "demand_actual.csv").open() as handle:
        reader = csv_module.DictReader(handle)
        first_row = next(reader)
    assert first_row["source_system"] == "synthetic_generator"
    assert first_row["load_id"] == "test-load"
    assert "was_stocked_out" in first_row


def test_write_raw_csvs_missing_promised_date_is_an_empty_field(tmp_path) -> None:
    from supply_planning.generator.run import generate_all, write_raw_csvs

    dataset = generate_all(seed=99, start_date=date(2026, 1, 5), end_date=date(2026, 4, 5))
    write_raw_csvs(dataset, tmp_path, load_id="test-load")

    import csv as csv_module

    missing_order_id = dataset.edge_cases.purchase_order.missing_promised_date
    with (tmp_path / "purchase_order_line.csv").open() as handle:
        reader = csv_module.DictReader(handle)
        matching = [row for row in reader if row["order_id"] == missing_order_id]
    assert len(matching) == 1
    assert matching[0]["promised_receipt_date"] == ""
