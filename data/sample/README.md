# Synthetic sample fixture — P1.3

> **This data is entirely synthetic**, produced by
> `src/supply_planning/generator/` (`scripts/generate_sample_data.py --preset sample`).
> It describes the fictional company Alpiflow SAS. It is not, and must never be
> presented as, a real extract. See `docs/BUSINESS_RULES.md` for the business
> frame and `docs/DATA_DICTIONARY.md` for the field-level definitions.

## How this was generated

```
PYTHONPATH=src python scripts/generate_sample_data.py --preset sample
```

- **Seed:** `2026` — re-running the command above reproduces these files byte-for-byte
  (the `extracted_at`/`load_id` ingestion-metadata columns are the only values that
  change between runs; every business column is identical).
- **Window:** `2026-03-02` → `2026-09-21` (30 weeks), a fixed, hard-coded window —
  not "today minus N weeks" — so this fixture never silently changes when
  regenerated later. Chosen to start inside the `FOOT`/`APPAREL` spring peak
  (`ASM-09`, ISO weeks 9–26) so the seasonality swing is visible in a short window.
- **Scale:** 120 SKUs (`ASM-01`), 6 suppliers, 2 purchase-order lines per SKU — a
  small, fixed set, not a scaled-down version of a larger simulation. The `full`
  preset (`--preset full`, gitignored under `data/raw/synthetic/`) generates the
  realistic ~3-year, same-120-SKU volume for load-testing ingestion/KPI logic; it
  is never committed.

## Deliberate edge cases

Each one exists so P1.4 (ingestion/quality checks) and P1.5 (KPI logic) have a
known, reproducible case to test against — see `docs/DATA_DICTIONARY.md` for why
each is a defect to *report*, not to silently repair.

| # | File | Case | Where |
|---|---|---|---|
| 1 | `demand_actual.csv` | `missing_sku_week` — the row for this product/week is entirely absent, not a zero | `APPAREL-001`, week `2026-09-21` |
| 2 | `demand_actual.csv` | A genuine 3-week run of zero demand, `was_stocked_out = False` — a true zero, not a defect and not a stockout | `APPAREL-002`, weeks `2026-03-02` / `2026-03-09` / `2026-03-16` |
| 3 | `inventory_snapshot.csv` | `negative_available_stock` — `allocated_qty > on_hand_qty` | `APPAREL-003`, snapshot `2026-03-02` |
| 4 | `purchase_order_line.csv` | Missing `promised_receipt_date` on an otherwise-normal received line — must be reported, never defaulted to `order_date + assumed lead time` | `order_id = PO-00001` (`APPAREL-001`) |
| 5 | `capacity.csv` | One family-week with `planned_load_units > available_capacity_units` (>100 % utilisation, not capped) | site `WH-01`, family `FOOT`, week `2026-06-15` |

Beyond these five, `purchase_order_line.csv` also deliberately cycles through
every documented `status` value and every OTIF outcome (on-time, late, early —
the delivery tolerance is 0 days per `ASM-06`, so early also fails — partial,
both cancellation reasons, still-open, and draft) across its 240 lines, so no
single status dominates the file by chance.

## Known limitation

Demand and inventory are generated independently per product-week (scaled by
family-level magnitude and safety-stock assumptions), not by simulating the full
demand → receipt → stock recurrence. P1.5 validates that recurrence by hand on its
own small, independently-constructed 3-week example — it does not depend on this
fixture's numbers being internally consistent across tables.
