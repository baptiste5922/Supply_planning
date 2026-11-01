"""dim_product generator (docs/DATA_DICTIONARY.md §1).

`docs/BUSINESS_RULES.md` §5 (`ASM-01`) only fixes the *total* active-SKU count
(~120); it does not say how that total splits across the four families. The split
below is this generator's own implementation detail, not a registered assumption -
it exists only so the total adds up to `assumptions.active_sku_count` in a
plausible way (FOOT dominates the row count because it is size-level, per
`docs/BUSINESS_RULES.md` §3 "main entity").
"""

from __future__ import annotations

import random
from dataclasses import dataclass

FOOT_SIZES: tuple[int, ...] = tuple(range(36, 48))  # 36-47 inclusive, per §1

# How the 120-SKU total (ASM-01) is split across families: 5 FOOT models x 12
# sizes = 60, plus 60 non-FOOT SKUs = 120. Not itself a registered assumption
# (ASM-01 only fixes the total); FOOT's model count is deliberately small because
# each model already expands into len(FOOT_SIZES) rows.
_FOOT_MODEL_COUNT = 5
_NON_FOOT_SKU_COUNT = {"APPAREL": 25, "PACK": 20, "NUTRI": 15}

_FOOT_MODEL_NAMES = ("Ridge", "Summit", "Crest", "Traverse", "Alpenglow")
_APPAREL_ITEM_NAMES = ("Windshell Jacket", "Trail Tee", "Thermal Sleeve", "Running Short")
_PACK_ITEM_NAMES = ("Hydration Vest 5L", "Hydration Vest 10L", "Trail Pole", "Running Belt")
_NUTRI_ITEM_NAMES = ("Energy Gel", "Energy Bar", "Electrolyte Tablet")


@dataclass(frozen=True)
class ProductRow:
    product_id: str
    product_name: str
    family: str
    size: str | None
    unit_of_measure: str


def generate_products(seed: int) -> list[ProductRow]:
    """Generate `dim_product` rows. Deterministic: the same seed and assumptions
    always produce the same rows, in the same order."""
    rng = random.Random(seed)
    rows: list[ProductRow] = []

    for model_index in range(_FOOT_MODEL_COUNT):
        model_name = _FOOT_MODEL_NAMES[model_index % len(_FOOT_MODEL_NAMES)]
        for size in FOOT_SIZES:
            rows.append(
                ProductRow(
                    product_id=f"FOOT-{model_index + 1:02d}-{size}",
                    product_name=f"{model_name} Trail Shoe",
                    family="FOOT",
                    size=str(size),
                    unit_of_measure="piece",
                )
            )

    name_pools = {
        "APPAREL": _APPAREL_ITEM_NAMES,
        "PACK": _PACK_ITEM_NAMES,
        "NUTRI": _NUTRI_ITEM_NAMES,
    }
    for family, sku_count in _NON_FOOT_SKU_COUNT.items():
        names = name_pools[family]
        for item_index in range(sku_count):
            name = names[item_index % len(names)]
            rows.append(
                ProductRow(
                    product_id=f"{family}-{item_index + 1:03d}",
                    product_name=f"{name} {item_index + 1:03d}",
                    family=family,
                    size=None,
                    unit_of_measure="piece",
                )
            )

    rng.shuffle(rows)  # avoid a suspiciously family-sorted raw extract
    return rows
