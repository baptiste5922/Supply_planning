# Data Dictionary — Alpiflow Supply Planning Control Tower

> **Disclaimer.** Alpiflow is a **fictional** company. Every field, value and example in this
> document is **synthetic**. See `docs/BUSINESS_RULES.md` for the business frame and the
> assumptions register, and `docs/ARCHITECTURE.md` for the three-schema data flow this dictionary
> feeds into.

- **Status:** v1 — P1.1
- **Date:** 2026-10-21
- **Scope:** the canonical field definitions for Phase 1 (Supply Planning Control Tower) only.
  This is the level of detail P1.2 will translate directly into `CREATE TABLE` statements under
  `sql/`.

## 0. How to read this document

- Each table below states its **grain** first — the one sentence that says what one row means.
  Get the grain wrong and every join and every KPI downstream is wrong, silently.
- Fields are defined at the **`clean`/`analytics` level** (per `docs/ARCHITECTURE.md` §3): the
  canonical, typed, keyed shape. The `raw` schema will mirror whatever columns the P1.3 generator
  or source files actually produce — it is documented when P1.3 defines those files, and must map
  onto the business fields defined here.
- **Missing-data rule** is listed explicitly per table/field because the project rule is "report,
  never guess" — see `docs/ARCHITECTURE.md` §2, ingestion "does not" column.
- Tables not yet in scope — `fct_demand_forecast` (Phase 2, see P2.2) and
  `fct_planning_exception` (an *output* of P1.5, not a source table) — are intentionally **not**
  defined here. Defining them now, before the logic that produces them exists, would mean
  guessing their shape.

---

## 1. `dim_product`

**Grain:** one row per sellable unit — one SKU, size-level for the `FOOT` family (per
`docs/BUSINESS_RULES.md` §3, "main entity"). Example: a single running-shoe model in size 42 is
one row; the same model in size 43 is a different row.

| Field | Type | Nullable | Key | Unit | Description |
|---|---|---|---|---|---|
| `product_id` | text | no | **PK** | — | Stable SKU code, assigned at the source. Natural key — no surrogate key is introduced in v1 because the dimension is small (~120 rows, `[ASM-01]`) and the code is already stable. |
| `product_name` | text | no | — | — | Human-readable name, for display only. |
| `family` | text | no | — | — | One of `FOOT`, `APPAREL`, `PACK`, `NUTRI` (`docs/BUSINESS_RULES.md` §1). Drives safety stock (`ASM-03`), lead time (`ASM-04`), MOQ (`ASM-07`) and capacity share (`ASM-11`) — all looked up by family in configuration, not stored redundantly here. |
| `size` | text | **yes** | — | — | Populated only for `FOOT` (e.g. `"42"`). `NULL` for every other family — this is a legitimate `NULL`, not missing data. |
| `unit_of_measure` | text | no | — | — | Constant `"piece"` for every row (`docs/BUSINESS_RULES.md` §3). Stored, not hard-coded, so a future unit change does not require a code change — but no conversion logic exists in v1. |

**Missing-data rule:** a row with a `NULL` or unrecognised `family` is rejected at ingestion and
reported, not defaulted to a guessed family — every downstream assumption lookup depends on it.

**Deferred (not a field in v1):** an `is_active` / end-of-life flag. `docs/BUSINESS_RULES.md` §6
leaves "collection end-of-life" an open question that affects **P1.2**, i.e. the next task, not
this one. Adding the column now would be inventing the answer early.

---

## 2. `dim_calendar`

**Grain:** one row per calendar date. Needed because inventory snapshots and purchase-order dates
are daily events, while demand and capacity are weekly (`docs/BUSINESS_RULES.md` §3) — this table
is what joins the two.

| Field | Type | Nullable | Key | Unit | Description |
|---|---|---|---|---|---|
| `calendar_date` | date | no | **PK** | — | One plain date, no time component (`docs/BUSINESS_RULES.md` §3 — timestamps are reduced to UTC dates before storage). |
| `week_start_date` | date | no | — | — | The Monday of the ISO week containing `calendar_date`. Many `calendar_date` rows share one `week_start_date` — this is the join key to every weekly fact table. |
| `iso_year` | integer | no | — | — | ISO week-numbering year (can differ from the calendar year in the last/first days of December). |
| `iso_week_number` | integer | no | — | 1–53 | ISO week number within `iso_year`. |

**Source of truth:** generated in Python, deterministic — never sourced from an ERP
(`docs/ARCHITECTURE.md` §4). By construction it cannot be "missing"; it must simply be generated
far enough forward to cover the full 13-week planning horizon past the current date.

**Deferred (not a field in v1):** a `season_label` column. No P1 KPI consumes it — `[ASM-09]`
seasonality windows matter for Phase 2 forecasting, not for the four Phase 1 KPIs. Adding it now
would violate "select the smallest set needed for the first vertical slice."

---

## 3. `dim_supplier`

**Grain:** one row per supplier.

| Field | Type | Nullable | Key | Unit | Description |
|---|---|---|---|---|---|
| `supplier_id` | text | no | **PK** | — | Stable supplier code. |
| `supplier_name` | text | no | — | — | Display name. |

**Deliberately excluded from this table:** `lead_time_weeks` and `minimum_order_qty`. Per
`docs/ARCHITECTURE.md` §4, lead time and MOQ are a **configuration** concern keyed by product
*family* (`[ASM-04]`, `[ASM-07]`), not a supplier master-data attribute — v1 has no credible
per-supplier lead-time source, and the planning logic must read one documented place, not two.
Putting them on `dim_supplier` would create a second, competing source of truth.

**Missing-data rule:** a purchase-order line referencing a `supplier_id` not present in this table
is rejected and reported — never silently inserted as a new supplier.

---

## 4. `fct_demand_actual` (sales)

**Grain:** one row per `product_id` × `week_start_date`. Demand is modelled **across the `D2C`
and `WHS` channels combined** — this is the v1 decision in `docs/BUSINESS_RULES.md` §1 ("Sales
channels"), because a single warehouse serves both and the replenishment decision is shared.

| Field | Type | Nullable | Key | Unit | Description |
|---|---|---|---|---|---|
| `product_id` | text | no | **PK, FK → dim_product** | — | |
| `week_start_date` | date | no | **PK, FK → dim_calendar** | — | |
| `units_sold` | integer | no | — | piece | Gross units sold that week, all channels combined. `>= 0`. |

**Missing-data rule — the important one:** every `product_id` that is active during a given
`week_start_date` **must have a row**, even when `units_sold = 0`. A missing row is a data-quality
defect (reported as `missing_sku_week`), not an implicit zero — a gap could equally mean "no
demand" or "the extract failed for that SKU." Collapsing the two would hide the second case.

**Known limitations, by explicit decision:**
- **Channel detail is not retained at this grain.** The `clean` layer may keep a per-channel
  breakdown closer to the source grain, but the Control Tower's planning fact aggregates to
  `product_id` × `week_start_date` only. A channel-level question cannot be answered from this
  table.
- **Returns are not modelled (P1.1 decision, `docs/BUSINESS_RULES.md` §6).** `units_sold` is
  gross; it is not corrected for later `D2C` sizing returns on `FOOT`. True consumer demand on
  `FOOT` is therefore slightly overstated. Accepted for v1 to avoid modelling the time lag between
  a sale and its later return before any schema exists; revisit in Phase 2 only if the EDA shows
  it matters.
- **Stockout censoring is a separate, still-open question** (`docs/BUSINESS_RULES.md` §6, affects
  P1.3) — whether a `was_stocked_out` flag is generated. Not a field here; decide it when P1.3
  builds the generator, not before.
- **Promotions** (`promotion_flag`) — open question affecting P2.3, deferred for the same reason.

---

## 5. `fct_inventory_snapshot`

**Grain:** one row per `product_id` × `site_id` × `snapshot_date`. In v1 there is one snapshot
per week, taken at the planning origin (Monday morning, reflecting Sunday-evening stock —
`docs/BUSINESS_RULES.md` §3).

| Field | Type | Nullable | Key | Unit | Description |
|---|---|---|---|---|---|
| `product_id` | text | no | **PK, FK → dim_product** | — | |
| `site_id` | text | no | **PK** | — | Constant `"WH-01"` in v1 (`docs/BUSINESS_RULES.md` §1). Kept as a real column, not a hard-coded assumption, so a future multi-site extension does not require a migration. |
| `snapshot_date` | date | no | **PK, FK → dim_calendar.calendar_date** | — | |
| `on_hand_qty` | integer | no | — | piece | Physical stock recorded at the source. `>= 0`. |
| `allocated_qty` | integer | no | — | piece | Stock already reserved to customer orders. `>= 0`. |

**`available_qty` is deliberately not a stored column.** It is a derived value,
`on_hand_qty - allocated_qty` (`[ASM-02]`), computed in `clean`/`analytics` — storing it would
create two sources of truth for one number. **If the subtraction would go negative, it is not
clamped to zero and not silently allowed through**: it is reported (`negative_available_stock`),
because it signals either a bad allocation or a stale snapshot, and clamping would hide exactly
the thing a planner needs to see.

**Missing-data rule:** if `product_id` has no snapshot for the current planning-origin week, the
SKU cannot be planned that week. This is reported as a blocker, not defaulted to `on_hand_qty = 0`
— zero stock is a real, meaningful value; "I don't know" is not the same fact and must not look
like it.

---

## 6. `fct_purchase_order_line` (purchase/supply)

**Grain:** one row per `order_id` × `product_id`. **Simplification, stated explicitly:** v1
assumes a given product appears at most once per purchase order — a split delivery is represented
by `status = partially_received` on that one line, not by a second line. If the P1.3 generator or
a later real source produces multiple lines for the same product on one order, this grain breaks
and must be revisited (tracked as a limitation, not silently worked around).

| Field | Type | Nullable | Key | Unit | Description |
|---|---|---|---|---|---|
| `order_id` | text | no | **PK** | — | |
| `product_id` | text | no | **PK, FK → dim_product** | — | |
| `supplier_id` | text | no | **FK → dim_supplier** | — | Denormalised onto the line rather than a separate order-header table — v1 has no other header-level field that would justify the extra table. |
| `order_date` | date | no | — | — | Date the order was confirmed. |
| `promised_receipt_date` | date | no | — | — | The date promised **at confirmation**. Immutable once set — `docs/BUSINESS_RULES.md` §4.4 requires this specifically so a supplier cannot reschedule and still read as "on time." |
| `actual_receipt_date` | date | **yes** | — | — | `NULL` until a receipt event occurs. |
| `ordered_qty` | integer | no | — | piece | `> 0`. |
| `received_qty` | integer | **yes** | — | piece | `NULL` while the line is still open (`status` in `confirmed`, `partially_received`'s "not yet finally received" sense — see below). Becomes a number, possibly `0`, once a receipt event or a cancellation fixes its final value. `NULL` and `0` are **not** interchangeable: `NULL` means "outcome unknown", `0` means "confirmed zero received." |
| `status` | text | no | — | — | One of `draft`, `confirmed`, `partially_received`, `received`, `cancelled_by_alpiflow`, `cancelled_by_supplier`. The two cancellation reasons are kept **distinct** because `docs/BUSINESS_RULES.md` §4.4 treats them differently in the OTIF KPI: Alpiflow-cancelled lines are excluded from the OTIF denominator, supplier-cancelled lines count as a failure. Collapsing them into one `cancelled` value would silently break that KPI. |

**Missing-data rule:** a line with `status` in `confirmed`/`partially_received`/`received` and a
`NULL` `promised_receipt_date` is a data-quality defect, reported and excluded from the shortage
and OTIF calculations until fixed — never defaulted to `order_date + assumed lead time`. (The
family-level lead-time assumption `[ASM-04]` is used only to *propose new* orders in P1.5; it is
not a substitute for a missing promised date on an order that already exists.)

---

## 7. `fct_capacity`

**Grain:** one row per `site_id` × `family` × `week_start_date`
(`docs/BUSINESS_RULES.md` §4.3 — capacity is a shared resource within a family, tracked at family
grain, not at SKU grain).

| Field | Type | Nullable | Key | Unit | Description |
|---|---|---|---|---|---|
| `site_id` | text | no | **PK** | — | Constant `"WH-01"` in v1. |
| `family` | text | no | **PK** | — | One of `FOOT`, `APPAREL`, `PACK`, `NUTRI`. |
| `week_start_date` | date | no | **PK, FK → dim_calendar** | — | |
| `available_capacity_units` | integer | no | — | piece/week | `= total_capacity_units × family_share` (`[ASM-05]` × `[ASM-11]`). Stored, not recomputed ad hoc in every query, so a configuration change is visible as a new row rather than a silent recalculation. |
| `planned_load_units` | integer | no | — | piece/week | Units of that family planned to be picked/shipped that week — sourced from the demand/supply plan, not from capacity. |

**Why this table needed a decision before it could be written:** `[ASM-05]` only specifies a
*single* 9,000 pieces/week figure for the whole site, but the KPI in `docs/BUSINESS_RULES.md`
§4.3 is defined at family grain. Splitting the total required a new, explicitly labelled
assumption — `[ASM-11]`, added in this task — rather than inventing a per-family number silently.
See `docs/BUSINESS_RULES.md` §4.3 and §5 for the resolution and its stated limitation (the split
is fixed, while a real warehouse could shift pickers between families within a week).

**Missing-data rule:** a week with no `fct_capacity` row for a family that has planned load is a
blocker — utilisation cannot be computed and must be reported, not treated as 0% or 100%.

---

## 8. Keys and grain, at a glance

| Table | Primary key | Grain in words |
|---|---|---|
| `dim_product` | `product_id` | one SKU |
| `dim_calendar` | `calendar_date` | one date |
| `dim_supplier` | `supplier_id` | one supplier |
| `fct_demand_actual` | `product_id`, `week_start_date` | one SKU, one week, all channels |
| `fct_inventory_snapshot` | `product_id`, `site_id`, `snapshot_date` | one SKU, one site, one weekly snapshot |
| `fct_purchase_order_line` | `order_id`, `product_id` | one product line on one purchase order |
| `fct_capacity` | `site_id`, `family`, `week_start_date` | one family's capacity, one site, one week |

## 9. Carried over from P1.1 into P1.2

- `dim_product.family` must be constrained to the four known codes (`CHECK` or lookup table — a
  decision for P1.2, not this document).
- `fct_purchase_order_line.status` must be constrained to the six listed values for the same
  reason.
- Every foreign key listed above must be enforced, not just documented — P1.2's acceptance
  criterion is "primary/foreign keys and relevant constraints are defined."
