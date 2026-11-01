#!/usr/bin/env python3
"""CLI entry point for the P1.4 ingestion pipeline.

Reads raw-shaped CSVs (`data/sample/` by default), loads `raw`, validates into
`clean`, copies into `analytics`, and logs the row counts and every
data-quality issue found (docs/ARCHITECTURE.md §2: "ingestion is logged and
reports row counts").
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from supply_planning.config import load_database_settings
from supply_planning.db import make_engine
from supply_planning.ingestion.run import run_ingestion

REPO_ROOT = Path(__file__).resolve().parent.parent

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("ingestion")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=REPO_ROOT / "data" / "sample")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    settings = load_database_settings()
    engine = make_engine(settings)

    logger.info("Ingesting %s into %s", args.input_dir, settings.sqlalchemy_url(hide_password=True))
    report = run_ingestion(engine, args.input_dir)

    for line in report.summary_lines():
        logger.info(line)
    logger.info("Total issues: %d", len(report.issues))
    for issue in report.issues:
        logger.info(
            "  [%s/%s] %s %s: %s", issue.table, issue.kind.value, issue.reason_code, issue.key, issue.detail
        )


if __name__ == "__main__":
    main()
