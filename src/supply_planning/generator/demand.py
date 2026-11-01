"""fct_demand_actual generator (docs/DATA_DICTIONARY.md §4).

Business logic encoded here:
  - seasonality by family (`ASM-09`, via `Assumptions.seasonality_peak_weeks`);
  - a per-SKU "popularity" level, fixed once per product so weeks are correlated
    over time instead of being pure independent noise - a modelling detail, not a
    registered assumption, needed for the generated series to look like a real
    product's demand rather than white noise;
  - stockout censoring (docs/BUSINESS_RULES.md §6, decided in P1.3): a small share
    of SKU-weeks are flagged `was_stocked_out`, with `units_sold` reduced below the
    true underlying demand that week - this is what "censored" means in the data
    dictionary: the number is real, but it understates demand.

Two edge cases are injected on purpose, and reported back via `DemandEdgeCases` so
a caller (or a test) can assert on them instead of re-discovering them by eye:
  - one SKU-week is *omitted entirely* -> the `missing_sku_week` data-quality case
    `docs/DATA_DICTIONARY.md` §4 requires ingestion to detect;
  - one SKU has a run of legitimate zero-demand weeks (not flagged as a defect).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date

from .assumptions import Assumptions, DEFAULT_ASSUMPTIONS
from .product import ProductRow

# Per-SKU weekly "popularity" range, by family - a generator-level magnitude choice
# (not an ASM-xx), set so NUTRI's "high turnover" and PACK's "stable demand"
# qualitative descriptions (docs/BUSINESS_RULES.md §1) translate into plausible
# numbers once seasonality is applied on top.
_POPULARITY_RANGE: dict[str, tuple[float, float]] = {
    "FOOT": (2.0, 12.0),
    "APPAREL": (4.0, 20.0),
    "PACK": (3.0, 10.0),
    "NUTRI": (8.0, 35.0),
}

_SEASONAL_PEAK_MULTIPLIER = 1.6
_SEASONAL_OFF_PEAK_MULTIPLIER = 0.7
_STOCKOUT_PROBABILITY = 0.04  # ~1 week in 25 per SKU, deliberately rare


@dataclass(frozen=True)
class DemandRow:
    product_id: str
    week_start_date: date
    units_sold: int
    was_stocked_out: bool


@dataclass(frozen=True)
class DemandEdgeCases:
    """Which deliberately-injected edge cases ended up where, for tests/docs."""

    missing_sku_week: tuple[str, date]
    zero_demand_run: tuple[str, tuple[date, ...]]


def _seasonal_multiplier(family: str, iso_week_number: int, assumptions: Assumptions) -> float:
    peak_ranges = assumptions.seasonality_peak_weeks[family]
    if not peak_ranges:
        return 1.0  # e.g. PACK: "more stable demand" (docs/BUSINESS_RULES.md §1)
    in_peak = any(start <= iso_week_number <= end for start, end in peak_ranges)
    return _SEASONAL_PEAK_MULTIPLIER if in_peak else _SEASONAL_OFF_PEAK_MULTIPLIER


def generate_demand(
    products: list[ProductRow],
    week_start_dates: list[date],
    seed: int,
    *,
    assumptions: Assumptions = DEFAULT_ASSUMPTIONS,
) -> tuple[list[DemandRow], DemandEdgeCases]:
    """Generate `fct_demand_actual` rows: one per product x week, minus the one
    deliberately-omitted week used as the `missing_sku_week` edge case."""
    rng = random.Random(seed)
    sorted_products = sorted(products, key=lambda p: p.product_id)
    sorted_weeks = sorted(week_start_dates)

    if len(sorted_products) < 2 or len(sorted_weeks) < 4:
        raise ValueError("need at least 2 products and 4 weeks to place the edge cases")

    missing_sku_week = (sorted_products[0].product_id, sorted_weeks[-1])
    zero_demand_product = sorted_products[1].product_id
    zero_demand_weeks = tuple(sorted_weeks[:3])  # first 3 weeks of history

    popularity: dict[str, float] = {
        product.product_id: rng.uniform(*_POPULARITY_RANGE[product.family])
        for product in sorted_products
    }

    rows: list[DemandRow] = []
    for product in sorted_products:
        for week_start in sorted_weeks:
            if (product.product_id, week_start) == missing_sku_week:
                continue  # the missing_sku_week edge case: no row at all

            if product.product_id == zero_demand_product and week_start in zero_demand_weeks:
                rows.append(
                    DemandRow(
                        product_id=product.product_id,
                        week_start_date=week_start,
                        units_sold=0,
                        was_stocked_out=False,  # a true zero, not a stockout
                    )
                )
                continue

            iso_week_number = week_start.isocalendar()[1]
            multiplier = _seasonal_multiplier(product.family, iso_week_number, assumptions)
            mean_demand = popularity[product.product_id] * multiplier
            true_demand = max(0, round(rng.gauss(mean_demand, mean_demand**0.5 * 0.6 + 0.5)))

            was_stocked_out = rng.random() < _STOCKOUT_PROBABILITY
            if was_stocked_out and true_demand > 0:
                # Only part of true demand could be served - the classic censoring
                # case this flag exists to make visible (docs/BUSINESS_RULES.md §6).
                units_sold = rng.randint(0, true_demand - 1) if true_demand > 1 else 0
            else:
                units_sold = true_demand
                was_stocked_out = False

            rows.append(
                DemandRow(
                    product_id=product.product_id,
                    week_start_date=week_start,
                    units_sold=units_sold,
                    was_stocked_out=was_stocked_out,
                )
            )

    edge_cases = DemandEdgeCases(
        missing_sku_week=missing_sku_week,
        zero_demand_run=(zero_demand_product, zero_demand_weeks),
    )
    return rows, edge_cases
