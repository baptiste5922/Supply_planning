#!/usr/bin/env python3
"""CLI entry point for the P1.5 planning run.

Computes the projected-inventory recurrence for every product in `analytics`
from a given planning origin, writes `analytics.fct_projected_inventory`, and
logs every data-quality issue and every replenishment suggestion found.
"""

from __future__ import annotations

import argparse
import logging
from datetime import date

from supply_planning.config import load_database_settings
from supply_planning.db import make_engine
from supply_planning.planning.run import run_planning

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("planning")

# A Monday within data/sample/'s fixed window (2026-03-02 -> 2026-09-21,
# data/sample/README.md) chosen so the full 13-week horizon and the 8-week
# trailing-average window both stay inside the fixture's known dates.
DEFAULT_PLANNING_ORIGIN = date(2026, 5, 4)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--planning-origin",
        type=date.fromisoformat,
        default=DEFAULT_PLANNING_ORIGIN,
        help="ISO date (a Monday), default %(default)s",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    settings = load_database_settings()
    engine = make_engine(settings)

    logger.info("Planning run from origin %s", args.planning_origin)
    result = run_planning(engine, planning_origin_date=args.planning_origin)

    logger.info("Rows written to analytics.fct_projected_inventory: %d", result.rows_written)
    logger.info("Quality issues: %d", len(result.report.issues))
    for issue in result.report.issues:
        logger.info(
            "  [%s/%s] %s %s: %s", issue.table, issue.kind.value, issue.reason_code, issue.key, issue.detail
        )

    logger.info("Replenishment suggestions: %d", len(result.proposed_orders))
    for order in result.proposed_orders:
        feasible = "OK" if order.is_feasible else "INFEASIBLE"
        logger.info(
            "  [%s] %s: order %d units now, receipt ~%s, covers week %d shortage (%d units)",
            feasible,
            order.product_id,
            order.suggested_quantity,
            order.suggested_receipt_date,
            order.shortage_week,
            order.shortage_units,
        )


if __name__ == "__main__":
    main()
