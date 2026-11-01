"""dim_supplier generator (docs/DATA_DICTIONARY.md §3).

No per-supplier lead time or MOQ here by design - those stay in `Assumptions`,
keyed by family (docs/DATA_DICTIONARY.md §3, docs/ARCHITECTURE.md §4).
"""

from __future__ import annotations

from dataclasses import dataclass

# Fixed, small and deterministic on purpose: a supplier list does not need a seed,
# the same six fictional suppliers exist in every generated dataset.
_SUPPLIERS: tuple[tuple[str, str], ...] = (
    ("SUP-01", "Pyrenees Textile Co."),
    ("SUP-02", "Dolomiti Footwear Group"),
    ("SUP-03", "Massif Central Outdoor Supply"),
    ("SUP-04", "Nordic Trail Nutrition"),
    ("SUP-05", "Alps Gear Manufacturing"),
    ("SUP-06", "Cevennes Pack & Carry"),
)


@dataclass(frozen=True)
class SupplierRow:
    supplier_id: str
    supplier_name: str


def generate_suppliers() -> list[SupplierRow]:
    """Generate `dim_supplier` rows. Fixed list, no seed needed."""
    return [SupplierRow(supplier_id=sid, supplier_name=name) for sid, name in _SUPPLIERS]
