# Business Rules — Alpiflow Trail Supply

> **Disclaimer.** Alpiflow is a **fictional** company. Every figure, dataset and rule in this
> document is **synthetic** and invented for an educational portfolio. Nothing here comes from
> Salomon, Amer Sports or any other real company. Every invented value carries an `[ASM-xx]`
> identifier and is listed in the assumptions register at the end of this document.

- **Status:** v1 — P0.1 (amended 2026-10-20 by P0.3: the "source of truth per field" open
  question is now answered in `docs/ARCHITECTURE.md` §4; amended 2026-10-21 by P1.1: the
  "e-commerce returns" open question is closed, and `ASM-11` is added to resolve a gap found
  while writing `docs/DATA_DICTIONARY.md`)
- **Date:** 2026-10-19
- **Structural decisions agreed:** grain SKU × week, 13-week horizon, single warehouse, unit = piece.

---

## 1. Fictional company

- **Name:** Alpiflow SAS
- **Business:** design and distribution of trail-running shoes and related running equipment
  (technical apparel, carrying gear, nutrition).
- **Simulated size:** ~120 active SKUs, ~€2.5M annual revenue. `[ASM-01]`

### Product families

| Code | Family | Contents | Expected demand behaviour |
|---|---|---|---|
| `FOOT` | Trail shoes | Models broken down by size (36–47) | Strong spring/autumn seasonality, short life cycle (collections), many slow-moving SKUs |
| `APPAREL` | Technical apparel | Jackets, shorts, tees, sleeves | Strong and inverted seasonality (jackets in winter, shorts in summer) |
| `PACK` | Carrying gear & accessories | Hydration vests, poles, belts, flasks | More stable demand, long life cycle |
| `NUTRI` | Nutrition & hydration | Gels, bars, electrolyte tablets | Regular demand, high turnover, peaks before major races |

> These four families were chosen because they have **different demand regimes**. A single KPI
> applied to all four should produce contrasting results — that is deliberate, and it will make
> the Phase 2 analyses more instructive.

### Sales channels

| Code | Channel | Characteristic |
|---|---|---|
| `D2C` | Direct e-commerce | Single-unit orders, smoother demand, returns possible |
| `WHS` | Specialist retailers | Bulk and less frequent orders, more "step-shaped" demand |

> **v1 decision:** demand is modelled **across all channels combined**. Channel is kept as an
> attribute but is not part of the planning grain. Reason: a single warehouse serves both
> channels, so the replenishment decision is shared.

### Planning site

- **One central warehouse**, code `WH-01`, Auvergne-Rhône-Alpes region.
- Consequence: inventory has no site dimension in v1. A `site_id` column is nevertheless kept in
  the schema, with a single value, so that a multi-site extension does not require a heavy
  migration.

### Intended users

| Role | What they expect from the system |
|---|---|
| Demand Planner | See historical demand and forecast per SKU-week, spot anomalies |
| Supply Planner | See projected inventory, upcoming shortages, decide this week's purchase orders |
| Purchasing Manager | Track supplier delivery performance and late orders |
| Supply Chain Director | Aggregated family view: coverage, excess stock, service level, warehouse load |

---

## 2. Decisions the system must support

1. **Which SKUs will run out of stock in the next 13 weeks, and in which week?**
2. **Which purchase orders must be placed this week**, for what quantity, given on-hand stock,
   expected receipts and supplier lead time?
3. **Where do we hold excess stock** that ties up cash and risks end-of-season markdown?
4. **Is warehouse picking capacity exceeded** in a given week, and by which family?
5. **Do suppliers deliver on the promised date**, and which ones degrade the plan?
6. **Is stock coverage per family aligned** with the defined service target?

> These six questions are the functional specification of the Phase 1 dashboard. Every visual in
> the Power BI report must answer at least one of them.

---

## 3. Planning grain and horizon

| Parameter | Value | Rationale |
|---|---|---|
| **Demand grain** | `SKU × week` | A daily grain is dominated by the day-of-week retail effect rather than by real demand; it produces many zeros and a precision the purchasing decision cannot consume. |
| **Main entity** | SKU (size-level for `FOOT`) | This is the level at which we order and hold stock. |
| **Planning horizon** | 13 rolling weeks | Covers the longest supplier lead time `[ASM-04]` plus a decision margin. |
| **History** | 2024-W01 → current week | ~3 years, enough annual cycles to estimate seasonality in Phase 2. |
| **Planning origin** | Monday of the current week | The plan is recomputed on Monday morning from Sunday-evening stock. |
| **Refresh frequency** | Weekly | Aligned with the Supply Planner's decision cycle. |
| **Week definition** | ISO 8601 week, starting **Monday**, identified by its `week_start_date` | Unambiguous standard, avoids US/EU convention clashes. |
| **Unit** | **Piece** everywhere (1 pair of shoes = 1 piece) | A single unit, no conversion, no ambiguity in the KPIs. |
| **Time zone** | Dates stored as **plain dates** (no timestamp); any timestamped extract is converted to **UTC** before being reduced to a date | Avoids week shifts at period boundaries. |

---

## 4. KPI definitions

Shared notation, for a week `t` and a SKU `s`:

- `OH_s` — available on-hand stock at the planning origin
- `D_{s,t}` — demand in week `t` (actual if past, forecast if future)
- `R_{s,t}` — supplier receipts expected in week `t` (orders already placed)
- `PI_{s,t}` — **projected inventory** at the end of week `t`
- `SS_s` — target safety stock

**Projected inventory balance equation** — the core of the Control Tower:

```
PI_{s,0} = OH_s
PI_{s,t} = PI_{s,t-1} + R_{s,t} - D_{s,t}      for t = 1..13
```

> This recurrence is the central calculation of the project. It must be reproducible **by hand**
> on a 3-week example (acceptance criterion of P1.5).

---

### 4.1 Weeks of Cover

- **Name:** `weeks_of_cover`
- **Formula:** the largest integer `k` such that cumulative demand over the next `k` weeks stays
  at or below available stock:
  `WoC_s = max { k ∈ [0, 13] : Σ_{t=1..k} D_{s,t} ≤ OH_s }`
- **Unit:** weeks
- **Grain:** one SKU, at the planning origin
- **Inventory definition used:** `OH` = physical stock **net of allocations** already reserved to
  customer orders `[ASM-02]`
- **Demand window:** **forward-looking** demand, not a historical average
- **Zero-demand handling:** if cumulative demand over 13 weeks is zero, coverage is **capped at 13**
  and the SKU is flagged `no_forward_demand = true`. It is **never** returned as infinite or as a
  silent `NULL`.
- **Interpretation:** "how many weeks I can last without replenishing"
- **Limitations:**
  - The forward-looking version depends on forecast quality — a bad forecast produces a wrong
    coverage with no visible signal.
  - Ignores expected receipts (deliberate: coverage measures the starting position, projected
    shortage measures the full plan).
  - An end-of-life SKU shows huge coverage, which is not a service problem but an excess-stock problem.

### 4.2 Projected shortage

- **Name:** `projected_shortage_units`
- **Formula:** `shortage_{s,t} = max(0, SS_s - PI_{s,t})`
- **Unit:** pieces
- **Grain:** one SKU × one week
- **First shortage week:** `first_shortage_week = min { t : PI_{s,t} < SS_s }`
- **Demand included:** actual demand for past weeks, forecast for future weeks. Both are **stored
  separately** and never mixed into the same column.
- **Supply included:** only **confirmed** purchase orders (statuses `confirmed` and
  `partially_received`). `draft` and `cancelled` orders are excluded.
- **Threshold:** the safety stock `SS_s`, defined per family `[ASM-03]`. A **negative** projected
  inventory is a certain shortage; a projected inventory between 0 and `SS_s` is a warning.
- **Missing-data handling:** if the supplier lead time is unknown, the SKU is **not** silently
  computed with a default value — it is raised in the data-quality report with reason
  `missing_lead_time`.
- **Limitations:** assumes receipts arrive on the promised date, which KPI 4.4 precisely shows to
  be false. The plan is therefore optimistic by construction.

### 4.3 Capacity utilisation

- **Name:** `capacity_utilisation_pct`
- **Formula:** `planned_load_{f,t} / available_capacity_{f,t} × 100`
- **Unit:** percentage; load and capacity both in **pieces processed per week**
- **Grain:** product family × week (not SKU: capacity is a shared resource)
- **Capacity unit:** pieces picked/shipped per week by warehouse `WH-01` `[ASM-05]`
- **Per-family capacity:** `ASM-05` only states a **total** of 9,000 pieces/week for the whole
  site. Because this KPI's grain is family × week, the total must be split by family — that split
  is `ASM-11` (see §5). `available_capacity_{f,t} = total_capacity_t × family_share_f`.
- **Overload handling:** the ratio is **not capped at 100%**. A value of 130% means the plan is
  infeasible, and that is exactly the information to surface. The system does not smooth or
  automatically defer the load.
- **Limitations:**
  - Capacity modelled as a simple weekly volume — no skills, shifts or overtime.
  - No distinction between inbound receiving and outbound shipping.
  - Distribution of the load within the week is ignored.
  - The family split (`ASM-11`) is a fixed percentage, not a measured capability — in reality a
    warehouse can shift pickers between families within a week, which would smooth out an
    apparent single-family overload. The KPI will over-report family-level infeasibility
    compared with the site's true flexibility.

### 4.4 Supplier delivery performance

- **Name:** `supplier_otif_pct` (On Time In Full, simplified)
- **Definition:** an order line is **OTIF** if it is received **in full**
  (`received_qty >= ordered_qty`) **and** on a date within the tolerance window around the
  promised date.
- **Formula:** `OTIF lines / lines due in the period × 100`
- **Date used:** `actual_receipt_date` compared with `promised_receipt_date` (the date promised at
  order confirmation, **not** a date rescheduled afterwards — otherwise a supplier can push their
  date back and stay "on time").
- **Tolerance:** 0 days early, 0 days late `[ASM-06]`
- **Denominator:** all lines whose promised date falls in the period, including those **never
  received** (a late undelivered line counts as a failure, not as missing data).
- **Partials and cancellations:** a partial receipt counts as a **failure**; a line cancelled by
  Alpiflow is **excluded** from the denominator; a line cancelled by the supplier counts as a
  **failure**.
- **Limitations:** measures success/failure only, not the magnitude of the delay. A one-day delay
  and a six-week delay carry the same weight.

---

## 5. Assumptions and synthetic data

All of these values are **invented**. They must be exposed in a configuration file and never
hard-coded into business logic.

| ID | Assumption | Value used | Why it is plausible |
|---|---|---|---|
| `ASM-01` | Company size | ~120 active SKUs, ~€2.5M revenue | Order of magnitude of a niche outdoor brand; small enough for a readable demo |
| `ASM-02` | Available stock is net of allocations | `available = on_hand - allocated` | Common distribution convention; avoids promising the same piece twice |
| `ASM-03` | Safety stock per family | `FOOT` 3 wks / `APPAREL` 3 wks / `PACK` 2 wks / `NUTRI` 2 wks of average demand | Families with long lead times and strong seasonality carry more cover |
| `ASM-04` | Supplier lead time per family | `FOOT` 10 wks (Asia) / `APPAREL` 8 wks / `PACK` 6 wks / `NUTRI` 3 wks (Europe) | Footwear is the longest to produce and the most distantly sourced |
| `ASM-05` | Warehouse `WH-01` capacity | 9,000 pieces picked per week, all families combined | Consistent with €2.5M revenue and an average basket around €60 |
| `ASM-06` | Delivery tolerance | 0 days | Deliberately strict definition so that the KPI produces visible failures |
| `ASM-07` | Minimum order quantity (MOQ) | `FOOT` 60 pcs / `APPAREL` 40 / `PACK` 25 / `NUTRI` 100 | Reflects usual production and packaging constraints |
| `ASM-08` | Service level target | 95% on `FOOT` and `APPAREL`, 98% on `NUTRI` | Nutrition is cheap to stock and highly substitutable: a stockout is costly in brand terms |
| `ASM-09` | Seasonality | `FOOT`/`APPAREL` peak March–June and September–October; `NUTRI` follows the race season | Real European trail-race calendar |
| `ASM-10` | Data period covered | 2024-W01 → current week (2026-10-19) | ~3 annual cycles, the minimum to estimate seasonality |
| `ASM-11` | Capacity split by family | `FOOT` 35% / `APPAREL` 25% / `NUTRI` 25% / `PACK` 15% of the 9,000 pcs/week total (`ASM-05`) | `FOOT` and `APPAREL` carry the most SKUs and revenue; `NUTRI` has high unit turnover despite a low unit price, so it earns a larger share than its revenue alone would suggest; `PACK` has the slowest velocity and the smallest share. Configurable, must sum to 100%. |

---

## 6. Open questions

To be decided before the related implementation. **Do not silently invent an answer.**

- [ ] **Stockout-censored sales.** When a SKU is out of stock, recorded sales are 0 even though
      real demand was positive. Should the data generator produce a `was_stocked_out` column to
      make censoring visible in Phase 2? *(affects P1.3 and P2.1)*
- [x] **E-commerce returns.** *Decided in P1.1:* returns are **ignored in v1**. `units_sold` in
      `analytics.fct_demand_actual` is gross, not corrected for later `D2C` returns. This is a
      known limitation (see `docs/DATA_DICTIONARY.md`, demand actual table): true consumer demand
      on `FOOT` is slightly overstated by the sizing-return rate. Revisit only if Phase 2 EDA shows
      the distortion materially affects the forecast.
- [ ] **Size substitution.** If size 42 is out of stock, does the customer take 43 or walk away?
      This changes the definition of a shortage for the `FOOT` family. *(affects P1.5)*
- [ ] **Collection end-of-life.** How do we represent a SKU replaced by next season's model?
      Should an inactive SKU disappear from the coverage calculation? *(affects P1.2 and P2.1)*
- [x] **Source of truth per field.** *Decided for Phases 1-2 in `docs/ARCHITECTURE.md` §4:*
      operational facts flow one way ERP -> analytics, Odoo wins on catalogue, stock and purchase
      orders, configuration owns the planning parameters, and this project owns only what it
      derives. The Phase 3 column remains **proposed** and must be re-confirmed in P3.5 once the
      shape of the Odoo test data is known. *(affects P3.5)*
- [ ] **Promotions.** Are promotion-driven demand peaks flagged with a `promotion_flag` usable by
      the forecasting model? *(affects P2.3)*
