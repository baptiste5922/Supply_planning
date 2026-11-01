"""Ingestion pipeline for the Alpiflow Control Tower (P1.4).

Reads raw-shaped CSVs (`data/sample/` by default, see `docs/ARCHITECTURE.md` §1),
loads them into `raw` as-is, validates each row against
`docs/DATA_DICTIONARY.md`'s per-table rules into `clean`, then copies `clean`
into `analytics` (identical shape in v1, per `docs/ARCHITECTURE.md` §3).

Every table module (`product.py`, `demand_actual.py`, ...) returns the rows it
loaded plus a `QualityReport` (`quality.py`) - invalid rows are reported, never
silently dropped or repaired (`docs/ARCHITECTURE.md` §2).
"""
