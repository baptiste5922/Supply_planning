#!/usr/bin/env python3
"""CLI entry point for the P1.3 synthetic-data generator.

Two presets, both built from the same generator functions (`src/supply_planning/
generator/`) so they can never silently diverge in shape:

  * `sample` (default) - a small, frozen window, written to `data/sample/` and
    committed to git (docs/ARCHITECTURE.md §5, `.gitignore`'s explicit exception
    for that directory). The dates are hard-coded, not "today minus N weeks",
    so re-running this script next year still reproduces the exact same fixture -
    the P1.3 acceptance criterion is reproducibility, which a wall-clock-relative
    window would quietly break.
  * `full` - the realistic ~120-SKU, 2024-W01-to-now dataset (`ASM-01`, `ASM-10`),
    written to `data/raw/synthetic/` (gitignored): useful to load-test the
    ingestion/KPI logic at scale, never committed.
"""

from __future__ import annotations

import argparse
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from supply_planning.generator.run import generate_all, write_raw_csvs

REPO_ROOT = Path(__file__).resolve().parent.parent

# Frozen on purpose (see module docstring): a Monday inside the FOOT/APPAREL
# spring peak window (ISO weeks 9-26, ASM-09) so a 30-week fixture already shows
# a season change, rather than one flat regime.
SAMPLE_SEED = 2026
SAMPLE_START_DATE = date(2026, 3, 2)
SAMPLE_WEEK_COUNT = 30

FULL_SEED = 2026
FULL_START_DATE = date(2024, 1, 1)  # 2024-W01, ASM-10
FULL_HORIZON_WEEKS = 13  # the planning horizon, docs/BUSINESS_RULES.md §3


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preset", choices=["sample", "full"], default="sample")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if args.preset == "sample":
        seed = args.seed if args.seed is not None else SAMPLE_SEED
        start_date = SAMPLE_START_DATE
        end_date = start_date + timedelta(weeks=SAMPLE_WEEK_COUNT - 1)
        output_dir = args.output_dir or (REPO_ROOT / "data" / "sample")
    else:
        seed = args.seed if args.seed is not None else FULL_SEED
        start_date = FULL_START_DATE
        end_date = date.today() + timedelta(weeks=FULL_HORIZON_WEEKS)
        output_dir = args.output_dir or (REPO_ROOT / "data" / "raw" / "synthetic")

    dataset = generate_all(seed=seed, start_date=start_date, end_date=end_date)
    load_id = f"{args.preset}-{uuid.uuid4()}"
    write_raw_csvs(
        dataset,
        output_dir,
        load_id=load_id,
        extracted_at=datetime.now(tz=timezone.utc),
    )

    print(f"Wrote {args.preset} dataset (seed={seed}, {start_date} -> {end_date}) to {output_dir}")
    print(f"load_id = {load_id}")
    print(f"Edge cases: {dataset.edge_cases}")


if __name__ == "__main__":
    main()
