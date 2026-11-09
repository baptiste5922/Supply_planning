"""Orchestrates one planning run (P1.5): reads `analytics` via SQLAlchemy,
computes the projected-inventory recurrence for every product with a usable
on-hand snapshot, and writes `analytics.fct_projected_inventory`.

Demand source, stated explicitly (see the P1.5 planning summary): until Phase 2
produces a real forecast, every week of the 13-week horizon - including weeks
that would be "future" relative to `planning_origin_date` - is read from
`analytics.fct_demand_actual`. If a required week has no row there, the
product is excluded from this run and reported (`missing_demand_data`), never
computed with a guessed value.

Average weekly demand (used to size `safety_stock_units` from `ASM-03`'s
"weeks of average demand") is the mean of the `AVERAGE_DEMAND_WINDOW_WEEKS`
weeks immediately before the origin - a generator-level interpretation of
`ASM-03`'s text, not itself a new registered assumption (same disclosure
pattern as P1.3's seasonality windows).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import Engine, text

from ..assumptions import Assumptions, DEFAULT_ASSUMPTIONS
from ..ingestion.db_writer import upsert_rows
from ..quality import IssueKind, QualityIssue, QualityReport
from .coverage import compute_weeks_of_cover
from .projected_inventory import HORIZON_WEEKS, compute_projected_inventory
from .replenishment import MissingLeadTimeError, ProposedOrder, propose_purchase_order

TABLE_NAME = "fct_projected_inventory"
PRIMARY_KEY = ("planning_origin_date", "product_id", "week_start_date")
AVERAGE_DEMAND_WINDOW_WEEKS = 8


@dataclass(frozen=True)
class PlanningRunResult:
    report: QualityReport
    proposed_orders: list[ProposedOrder]
    rows_written: int


def _horizon_weeks(origin: date) -> list[date]:
    return [origin + timedelta(weeks=i) for i in range(1, HORIZON_WEEKS + 1)]


def run_planning(
    engine: Engine,
    *,
    planning_origin_date: date,
    assumptions: Assumptions = DEFAULT_ASSUMPTIONS,
) -> PlanningRunResult:
    report = QualityReport()
    horizon_weeks = _horizon_weeks(planning_origin_date)
    trailing_start = planning_origin_date - timedelta(weeks=AVERAGE_DEMAND_WINDOW_WEEKS)

    with engine.connect() as conn:
        products = conn.execute(
            text("SELECT product_id, family FROM analytics.dim_product")
        ).mappings().all()

        on_hand_by_product: dict[str, int] = {
            row["product_id"]: row["on_hand_qty"] - row["allocated_qty"]
            for row in conn.execute(
                text(
                    """
                    SELECT DISTINCT ON (product_id) product_id, on_hand_qty, allocated_qty
                    FROM analytics.fct_inventory_snapshot
                    WHERE snapshot_date <= :origin
                    ORDER BY product_id, snapshot_date DESC
                    """
                ),
                {"origin": planning_origin_date},
            ).mappings()
        }

        average_demand_by_product: dict[str, float] = {
            row["product_id"]: float(row["avg_units"])
            for row in conn.execute(
                text(
                    """
                    SELECT product_id, AVG(units_sold) AS avg_units
                    FROM analytics.fct_demand_actual
                    WHERE week_start_date >= :start AND week_start_date < :origin
                    GROUP BY product_id
                    """
                ),
                {"start": trailing_start, "origin": planning_origin_date},
            ).mappings()
        }

        demand_by_product: dict[str, dict[date, int]] = {}
        for row in conn.execute(
            text(
                """
                SELECT product_id, week_start_date, units_sold
                FROM analytics.fct_demand_actual
                WHERE week_start_date = ANY(:weeks)
                """
            ),
            {"weeks": horizon_weeks},
        ).mappings():
            demand_by_product.setdefault(row["product_id"], {})[row["week_start_date"]] = row["units_sold"]

        receipts_by_product: dict[str, dict[date, int]] = {}
        for row in conn.execute(
            text(
                """
                SELECT pol.product_id, cal.week_start_date, SUM(pol.ordered_qty) AS receipt_units
                FROM analytics.fct_purchase_order_line pol
                JOIN analytics.dim_calendar cal ON cal.calendar_date = pol.promised_receipt_date
                WHERE pol.status IN ('confirmed', 'partially_received')
                  AND cal.week_start_date = ANY(:weeks)
                GROUP BY pol.product_id, cal.week_start_date
                """
            ),
            {"weeks": horizon_weeks},
        ).mappings():
            receipts_by_product.setdefault(row["product_id"], {})[row["week_start_date"]] = int(
                row["receipt_units"]
            )

    computed_at = datetime.now(tz=timezone.utc)
    output_rows: list[dict[str, Any]] = []
    proposed_orders: list[ProposedOrder] = []

    for product in products:
        product_id = product["product_id"]
        family = product["family"]

        if product_id not in on_hand_by_product:
            report.add(
                QualityIssue(
                    TABLE_NAME,
                    IssueKind.MISSING,
                    "missing_inventory_snapshot",
                    (product_id,),
                    f"no inventory snapshot at or before {planning_origin_date}",
                )
            )
            continue

        weekly_demand = demand_by_product.get(product_id, {})
        missing_weeks = [week for week in horizon_weeks if week not in weekly_demand]
        if missing_weeks:
            report.add(
                QualityIssue(
                    TABLE_NAME,
                    IssueKind.MISSING,
                    "missing_demand_data",
                    (product_id,),
                    f"no demand figure for {len(missing_weeks)} week(s), e.g. {missing_weeks[0]}",
                )
            )
            continue

        on_hand_available = on_hand_by_product[product_id]
        safety_stock_units = round(
            assumptions.safety_stock_weeks[family] * average_demand_by_product.get(product_id, 0.0)
        )
        weekly_receipts = receipts_by_product.get(product_id, {})

        pi_rows = compute_projected_inventory(
            on_hand_available=on_hand_available,
            safety_stock_units=safety_stock_units,
            horizon_weeks=horizon_weeks,
            weekly_demand=weekly_demand,
            weekly_confirmed_receipts=weekly_receipts,
        )
        coverage = compute_weeks_of_cover(
            on_hand_available=on_hand_available, horizon_weeks=horizon_weeks, weekly_demand=weekly_demand
        )

        for pi_row in pi_rows:
            is_origin = pi_row.weeks_ahead == 0
            output_rows.append(
                {
                    "planning_origin_date": planning_origin_date,
                    "product_id": product_id,
                    # The origin row (t=0) has no week of its own in the recurrence
                    # (projected_inventory.py's ProjectedInventoryWeek.week_start_date
                    # is None there) - persisted here as the origin's own calendar
                    # week, since the PK column cannot be NULL.
                    "week_start_date": pi_row.week_start_date or planning_origin_date,
                    "weeks_ahead": pi_row.weeks_ahead,
                    "demand_units": pi_row.demand_units,
                    "confirmed_receipt_units": pi_row.confirmed_receipt_units,
                    "projected_inventory_units": pi_row.projected_inventory_units,
                    "safety_stock_units": pi_row.safety_stock_units,
                    "projected_shortage_units": pi_row.projected_shortage_units,
                    "weeks_of_cover": coverage.weeks_of_cover if is_origin else None,
                    "no_forward_demand": coverage.no_forward_demand if is_origin else None,
                    "computed_at": computed_at,
                }
            )

        try:
            suggestion = propose_purchase_order(
                product_id=product_id,
                family=family,
                order_reference_date=planning_origin_date,
                projected_inventory_weeks=pi_rows,
                lead_time_weeks=assumptions.lead_time_weeks,
                moq_units=assumptions.moq_units,
            )
        except MissingLeadTimeError as exc:
            report.add(
                QualityIssue(TABLE_NAME, IssueKind.MISSING, "missing_lead_time", (product_id,), str(exc))
            )
        else:
            if suggestion is not None:
                proposed_orders.append(suggestion)
                if not suggestion.is_feasible:
                    report.add(
                        QualityIssue(
                            TABLE_NAME,
                            IssueKind.FLAGGED,
                            "infeasible_replenishment",
                            (product_id,),
                            f"lead time cannot deliver before week {suggestion.shortage_week}'s shortage",
                        )
                    )

    rows_written = upsert_rows(
        engine, schema="analytics", table_name=TABLE_NAME, rows=output_rows, primary_key=PRIMARY_KEY
    )

    return PlanningRunResult(report=report, proposed_orders=proposed_orders, rows_written=rows_written)
