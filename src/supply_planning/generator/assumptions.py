"""Business assumptions behind the synthetic dataset (docs/BUSINESS_RULES.md §5).

Every value here is invented for the fictional company Alpiflow and carries its
`ASM-xx` id in a comment so it can be traced back to the register in
`docs/BUSINESS_RULES.md`. Collected once so the demand, inventory, purchase-order
and capacity generators read the same number instead of each hard-coding its own
copy — the project rule is "assumptions live in configuration, not in logic".
"""

from __future__ import annotations

from dataclasses import dataclass

FAMILIES: tuple[str, ...] = ("FOOT", "APPAREL", "PACK", "NUTRI")


@dataclass(frozen=True)
class Assumptions:
    """One frozen set of ASM-xx values, keyed by family where the rule varies by family."""

    active_sku_count: int  # ASM-01
    safety_stock_weeks: dict[str, float]  # ASM-03
    lead_time_weeks: dict[str, int]  # ASM-04
    total_capacity_units_per_week: int  # ASM-05
    otif_tolerance_days: int  # ASM-06
    moq_units: dict[str, int]  # ASM-07
    seasonality_peak_weeks: dict[str, tuple[tuple[int, int], ...]]  # ASM-09, see note below
    capacity_share: dict[str, float]  # ASM-11

    def __post_init__(self) -> None:
        for field_name, values in (
            ("safety_stock_weeks", self.safety_stock_weeks),
            ("lead_time_weeks", self.lead_time_weeks),
            ("moq_units", self.moq_units),
            ("seasonality_peak_weeks", self.seasonality_peak_weeks),
            ("capacity_share", self.capacity_share),
        ):
            missing = [family for family in FAMILIES if family not in values]
            if missing:
                raise ValueError(f"{field_name} is missing families: {missing}")

        share_total = sum(self.capacity_share.values())
        if abs(share_total - 1.0) > 1e-9:
            raise ValueError(f"capacity_share (ASM-11) must sum to 1.0, got {share_total}.")


# ASM-09 states the seasonality qualitatively ("FOOT/APPAREL peak March-June and
# September-October; NUTRI follows the race season"), not as ISO week numbers. The
# ranges below are this generator's own translation of that text into concrete weeks
# — a generator-level implementation detail, not a new registered assumption. It is
# still passed through `Assumptions` (not hard-coded in demand.py) so it stays
# configurable and visible in one place.
DEFAULT_ASSUMPTIONS = Assumptions(
    active_sku_count=120,
    safety_stock_weeks={"FOOT": 3, "APPAREL": 3, "PACK": 2, "NUTRI": 2},
    lead_time_weeks={"FOOT": 10, "APPAREL": 8, "PACK": 6, "NUTRI": 3},
    total_capacity_units_per_week=9_000,
    otif_tolerance_days=0,
    moq_units={"FOOT": 60, "APPAREL": 40, "PACK": 25, "NUTRI": 100},
    seasonality_peak_weeks={
        "FOOT": ((9, 26), (35, 44)),  # ~March-June, ~September-October
        "APPAREL": ((9, 26), (35, 44)),
        "PACK": (),  # ASM-09 only calls out FOOT, APPAREL and NUTRI
        "NUTRI": ((14, 26), (31, 39)),  # spring races, then late-summer races (UTMB window)
    },
    capacity_share={"FOOT": 0.35, "APPAREL": 0.25, "NUTRI": 0.25, "PACK": 0.15},
)
