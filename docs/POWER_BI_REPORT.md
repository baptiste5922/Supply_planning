# Power BI Report — Alpiflow Supply Planning Control Tower

> **Disclaimer.** Alpiflow is a **fictional** company and every dataset in this report is
> **synthetic**. See `docs/BUSINESS_RULES.md` for the business frame and `docs/DATA_DICTIONARY.md`
> for the field-level source of every table named below.

- **Status:** v1 — P1.6, in progress. §1–§3 (semantic model, DAX measures, page spec) are written
  and the §2 validation queries have been run against the local dev database. **The `.pbix` itself
  does not exist yet** — Power BI Desktop requires Windows and this is being built on a Mac with no
  Windows VM available. §4 is the checklist to execute on a Windows PC to finish the build. The
  roadmap (`docs/ROADMAP.md`) keeps P1.6 at `IN_PROGRESS`, not `DONE`, until that happens — a
  specification is not a report, and P1.6's acceptance criteria explicitly require screenshots.
- **Date:** 2026-11-11 (model and measures), 2026-11-17 (page spec, SQL validation run, build
  checklist)
- **Scope:** the semantic model, DAX measures and report-page specification for the Phase 1
  Control Tower report. Built in Power BI Desktop (Windows VM), published to Power BI Service.

This document is written **before** the report is built. Per `docs/ARCHITECTURE.md` §2, Power BI's
job is to "filter, aggregate, present" — it must **reconcile** every SQL-defined KPI, never
reinterpret the formula. Writing the model and measures down first, with their validation query,
is what makes that reconciliation checkable rather than a hope.

---

## 1. Semantic model

### 1.1 Tables imported into Power BI

**Import mode, not DirectQuery** (decision, not in `docs/BUSINESS_RULES.md`'s assumption register
because it is a reporting-tool choice, not a business one): the `.pbix` must open and show numbers
even when the local PostgreSQL dev instance is not running — important for a demo in an interview
setting. Consequence, stated once so it is not rediscovered as a surprise: after a new
`run_planning.py` or `run_ingestion.py` run, the report needs an explicit **Refresh**, it does not
update live.

| Table | PostgreSQL source | Role |
|---|---|---|
| `dim_product` | `analytics.dim_product` | Dimension |
| `dim_calendar` | `analytics.dim_calendar` | Dimension (see §1.4 — also the Date table) |
| `dim_supplier` | `analytics.dim_supplier` | Dimension |
| `fct_demand_actual` | `analytics.fct_demand_actual` | Fact |
| `fct_inventory_snapshot` | `analytics.fct_inventory_snapshot` | Fact |
| `fct_purchase_order_line` | `analytics.fct_purchase_order_line` | Fact |
| `fct_capacity` | `analytics.fct_capacity` | Fact |
| `fct_projected_inventory` | `analytics.fct_projected_inventory` | Fact (P1.5 output) |

**Deliberately not imported: `analytics.v_capacity_utilisation` and `analytics.v_supplier_otif`.**
Both views pre-aggregate away the detail (`v_supplier_otif` collapses to one row per supplier,
`v_capacity_utilisation` already matches `fct_capacity`'s own grain so it adds nothing as a
separate import). P1.6's acceptance criterion requires **product/time filtering to work** on every
important measure — a pre-aggregated view can't be sliced further. Instead, §2 rebuilds each view's
*exact formula* as a DAX measure over the base fact table, with the view's own SQL kept as the
validation query. This is the same "reconcile, don't reinterpret" rule applied one level down: the
*formula* is never re-derived, only its evaluation context changes from "fixed by the view" to
"whatever the report page filters to."

### 1.2 Relationships

| From (fact, column) | To (dimension, column) | Cardinality | Active? |
|---|---|---|---|
| `fct_demand_actual.product_id` | `dim_product.product_id` | many-to-one | yes |
| `fct_demand_actual.week_start_date` | `dim_calendar.calendar_date` | many-to-one | yes |
| `fct_inventory_snapshot.product_id` | `dim_product.product_id` | many-to-one | yes |
| `fct_inventory_snapshot.snapshot_date` | `dim_calendar.calendar_date` | many-to-one | yes |
| `fct_purchase_order_line.product_id` | `dim_product.product_id` | many-to-one | yes |
| `fct_purchase_order_line.supplier_id` | `dim_supplier.supplier_id` | many-to-one | yes |
| `fct_purchase_order_line.promised_receipt_date` | `dim_calendar.calendar_date` | many-to-one | yes |
| `fct_capacity.week_start_date` | `dim_calendar.calendar_date` | many-to-one | yes |
| `fct_projected_inventory.product_id` | `dim_product.product_id` | many-to-one | yes |
| `fct_projected_inventory.week_start_date` | `dim_calendar.calendar_date` | many-to-one | **yes** |

`fct_projected_inventory.planning_origin_date` gets **no relationship to `dim_calendar` at all** —
see §1.3 for why, and why that is a deliberate "not needed" rather than an oversight.

Two columns of `fct_purchase_order_line` are **not** related to `dim_calendar` at all:
`order_date` and `actual_receipt_date`. Only `promised_receipt_date` gets a relationship, because
every report-level question in `docs/BUSINESS_RULES.md` §2 ("which lines are due", "which suppliers
are late") is asked against the *promised* date — `docs/BUSINESS_RULES.md` §4.4 is explicit that
OTIF must be judged against the promised date, never a rescheduled one. The OTIF measure in §2.3
still *reads* `actual_receipt_date` — but as a plain row-level column compared to
`promised_receipt_date` inside the measure itself, not through a calendar relationship. Building a
relationship nobody filters by yet would be exactly the premature abstraction the project avoids
elsewhere (`CLAUDE.md` — "don't design for hypothetical future requirements").

### 1.3 The role-playing dimension: two dates, one fact table

`fct_projected_inventory` has **two** date columns that could point at `dim_calendar`:
`week_start_date` (which week this row is *about*) and `planning_origin_date` (which Monday the
plan was *computed from*, `docs/DATA_DICTIONARY.md` §8). Power BI allows only **one active**
relationship between any two tables — a second relationship between the same pair must be
inactive (reactivated only inside a specific measure via `USERELATIONSHIP`), or the model is
ambiguous and Power BI refuses to pick a side for you.

**Resolved — and sharper than "out of date":** with the single planning run currently in the
sample data (origin `2026-05-04`), a chart with `week_start_date` on the x-axis and
`projected_inventory_units` summed, **not** filtered on `planning_origin_date`, shows the **correct**
number today — there is only one value for the origin, so no row can collide with another. The
real failure mode shows up the moment a **second** run exists (say, origin `2026-05-11` next
Monday): because `weeks_ahead = 0`'s row stores `week_start_date = planning_origin_date`
(`docs/DATA_DICTIONARY.md` §8), the new run's `t=0` row and an older run's `t=1` row can land on
the **same** `week_start_date` for the **same** product. `SUM()` without an origin filter would
then silently add both runs' numbers together for that week — not a stale number, a **double-
counted** one that still looks plausible.

**Design consequence:** `planning_origin_date` does not need a relationship to `dim_calendar` at
all — not even an inactive one. It is used only as a **direct filter on the fact table's own
column** (a slicer on `fct_projected_inventory[planning_origin_date]`, with no calendar hierarchy
involved), present on every page that reads this table. §3's page spec adds a visible
**"Plan computed from: `<date>`"** card next to that slicer on every such page — the skill's rule
that a dashboard must "display units, time period and data freshness" applies directly here, and
it is the simplest way to make the selected origin impossible to miss. A "default to the latest
origin automatically" DAX pattern was considered and rejected for v1: it cannot be verified against
real double-run data yet (only one run exists), and an unverified correctness claim is worse than
an explicit, visible slicer. Revisit once a second `run_planning.py` run genuinely exists to test
against.

### 1.4 `dim_calendar` as the Date table

`calendar_date` is marked **"Mark as date table"** in Power BI (Modeling ribbon), using
`calendar_date` as the key column. This is what makes Power BI treat the column as a real calendar
rather than a bag of dates — required for correct sorting of week/date axes and for any time-
intelligence function, even though the four KPIs in `docs/BUSINESS_RULES.md` §4 do not use
year-over-year comparisons in v1.

One calculated column is added directly on `dim_calendar` (row-level, stored — not a measure,
per the project's "calculated column only when row-level logic is appropriate" rule):

```dax
Week Label = dim_calendar[iso_year] & "-W" & FORMAT(dim_calendar[iso_week_number], "00")
```

Used as the axis label on every weekly chart instead of the raw date, so "2026-W19" reads instead
of "2026-05-04" — the ISO week identity `docs/BUSINESS_RULES.md` §3 already committed to.

### 1.5 Connection

Power BI Desktop → **Get Data → PostgreSQL database** → server `localhost:5433` (or the VM's
reachable host/port for the dev instance), database `supply_planning_lab`, schema `analytics`
tables only (never `raw` or `clean` — Power BI is a *consumption* layer, per
`docs/ARCHITECTURE.md` §2, it has no business reading pre-validation data). Credentials: the same
least-privilege `supply_planning_app` role already used by the Python pipeline (`.env`,
never committed).

### 1.6 What this model cannot answer (disclosed now, not discovered later)

Cross-checking against the six decisions in `docs/BUSINESS_RULES.md` §2:

- **Decision 2** ("which purchase orders must be placed this week, what quantity") — P1.5's
  `replenishment.py` computes a suggested order, but the session log states explicitly it is
  **not persisted to any table**. This model can show *that* a SKU has a shortage and *when*
  (`first_shortage_week`, derivable from `fct_projected_inventory`), but not the suggested order
  quantity or date. The report page for this decision will say so rather than fake a number.
- **Decision 3** ("where do we hold excess stock that ties up cash") — no unit cost exists
  anywhere in `docs/DATA_DICTIONARY.md`. The report can show excess stock in **pieces** (high
  `weeks_of_cover`, high `on_hand_qty`) but never in currency. Stated as a limitation on the page,
  not silently answered in units and left ambiguous.

---

## 2. DAX measures

One measure per KPI in `docs/BUSINESS_RULES.md` §4, each with its validation query. Every measure
below must be checked against the SQL **at the same filter context** (same `planning_origin_date`,
same product/family/supplier slicer) before the report is considered built — this is the literal
meaning of P1.6's acceptance criterion "important measures reconcile to SQL."

**One DAX subtlety used repeatedly below, stated once:** `CALCULATE`'s filter arguments can
compare a column to a constant directly (`Table[Col] = value`), but comparing **two columns of the
same row** to each other (as OTIF's "received on the promised date" must) requires an explicit
`FILTER(Table, ...)` — `CALCULATE` silently cannot do a column-to-column test as a bare boolean
argument the way it can with a constant.

### 2.1 Weeks of Cover (`docs/BUSINESS_RULES.md` §4.1)

The value is already computed in Python (P1.5) and stored once per `(planning_origin_date,
product_id)` at `weeks_ahead = 0` only (`NULL` elsewhere, `docs/DATA_DICTIONARY.md` §8) — the
measure's job is to **read it at the right row**, not recompute it.

```dax
Weeks of Cover =
CALCULATE(
    AVERAGE(fct_projected_inventory[weeks_of_cover]),
    fct_projected_inventory[weeks_ahead] = 0
)
```

```dax
SKUs - No Forward Demand =
CALCULATE(
    DISTINCTCOUNT(fct_projected_inventory[product_id]),
    fct_projected_inventory[weeks_ahead] = 0,
    fct_projected_inventory[no_forward_demand] = TRUE()
)
```

The second measure exists because **averaging hides the capped-at-13 cases**
(`docs/BUSINESS_RULES.md` §4.1's "never infinite or silent NULL" rule) — a handful of
`no_forward_demand = true` SKUs pull the average up without that being visible, unless this count
sits next to it on the page.

**Validation:**
```sql
SELECT product_id, weeks_of_cover, no_forward_demand
FROM analytics.fct_projected_inventory
WHERE planning_origin_date = '2026-05-04' AND weeks_ahead = 0;
```

### 2.2 Projected shortage (`docs/BUSINESS_RULES.md` §4.2)

```dax
Projected Shortage (Units) = SUM(fct_projected_inventory[projected_shortage_units])
```

```dax
SKUs With Shortage =
CALCULATE(
    DISTINCTCOUNT(fct_projected_inventory[product_id]),
    fct_projected_inventory[projected_shortage_units] > 0
)
```

```dax
First Shortage Week =
CALCULATE(
    MIN(fct_projected_inventory[week_start_date]),
    fct_projected_inventory[projected_shortage_units] > 0
)
```

**Disclose on the page, not just here:** the P1.5 session log already recorded that 117 of 120
sample SKUs show a shortage, a known effect of demand and inventory being generated independently
(`data/sample/README.md`), not a report bug. `SKUs With Shortage` will look alarming the first
time it renders — §3 adds a text box next to it saying so, instead of leaving a viewer to wonder
if the dashboard is broken.

**Validation:**
```sql
SELECT product_id, SUM(projected_shortage_units) AS total_shortage,
       MIN(week_start_date) FILTER (WHERE projected_shortage_units > 0) AS first_shortage_week
FROM analytics.fct_projected_inventory
WHERE planning_origin_date = '2026-05-04'
GROUP BY product_id;
```

### 2.3 Capacity utilisation (`docs/BUSINESS_RULES.md` §4.3)

Rebuilt from `fct_capacity` to match `analytics.v_capacity_utilisation`'s formula **row for row**,
including its `WHERE available_capacity_units > 0` exclusion — applied inside the measure, not
left for `DIVIDE`'s blank-on-zero behaviour to paper over, because the view doesn't just avoid a
division by zero, it drops the row entirely from both sides of the ratio:

```dax
Capacity Utilisation % =
VAR LoadWithCapacity =
    CALCULATE(
        SUM(fct_capacity[planned_load_units]),
        fct_capacity[available_capacity_units] > 0
    )
VAR CapacityAvailable =
    CALCULATE(
        SUM(fct_capacity[available_capacity_units]),
        fct_capacity[available_capacity_units] > 0
    )
RETURN
    DIVIDE(LoadWithCapacity, CapacityAvailable) * 100
```

**Deliberately not capped at 100%** — same reason as the SQL view: `docs/BUSINESS_RULES.md` §4.3
states an overload must be visible, not smoothed.

**Validation:**
```sql
SELECT * FROM analytics.v_capacity_utilisation
WHERE family = 'FOOT' AND week_start_date = '2026-06-15';
-- expected: 122.3 (P1.5 session log)
```

### 2.4 Supplier OTIF (`docs/BUSINESS_RULES.md` §4.4)

The column-to-column comparison from this section's opening note shows up here: "received exactly
on the promised date" compares two columns of the same row, so it needs `FILTER`, not a bare
boolean argument.

```dax
OTIF Lines =
CALCULATE(
    COUNTROWS(fct_purchase_order_line),
    FILTER(
        fct_purchase_order_line,
        fct_purchase_order_line[status] = "received"
            && fct_purchase_order_line[actual_receipt_date] = fct_purchase_order_line[promised_receipt_date]
    )
)
```

```dax
Lines Due =
CALCULATE(
    COUNTROWS(fct_purchase_order_line),
    fct_purchase_order_line[status] <> "cancelled_by_alpiflow",
    fct_purchase_order_line[promised_receipt_date] <= TODAY()
)
```

```dax
Supplier OTIF % = DIVIDE([OTIF Lines], [Lines Due]) * 100
```

These two filter arguments **are** plain column-to-constant comparisons (`<> "cancelled_by_alpiflow"`,
`<= TODAY()`), so no `FILTER()` is needed for them — only the OTIF-date comparison needed it. This
contrast is worth noticing once, since it is easy to over-apply `FILTER()` everywhere "to be safe"
once you've seen it solve one case.

**Validation:**
```sql
SELECT * FROM analytics.v_supplier_otif WHERE supplier_id = '<pick one from dim_supplier>';
-- expect roughly 33% overall (P1.5 session log), per-supplier values will vary
```

---

## 3. Report pages

Each page is built to answer specific numbered decisions from `docs/BUSINESS_RULES.md` §2 — the
rule stated there ("every visual must answer at least one of them") is the test applied below,
page by page. Every page shares three fixed elements, placed in the same spot on every page so a
viewer does not have to relearn the layout:

- **A synthetic-data banner** (top of page, small text box): *"Alpiflow is a fictional company.
  All figures are generated synthetic data — see `docs/BUSINESS_RULES.md`."* This is the literal
  implementation of P1.6's "synthetic data is disclosed" acceptance criterion — on the report
  itself, not only in a README a viewer may never open.
- **A family slicer** (`dim_product[family]`) and a **product/SKU slicer** (`dim_product
  [product_id]`), both visible, not hidden in a filter pane — this is what "product filtering
  works" means as a testable behaviour rather than a claim.
- **A week slicer** on `dim_calendar[Week Label]` (§1.4) for every page reading
  `fct_demand_actual`, `fct_inventory_snapshot` or `fct_capacity` — this is "time filtering works."

Pages reading `fct_projected_inventory` add a fourth fixed element instead of the week slicer:
the **`planning_origin_date` slicer plus the "Plan computed from: `<date>`" card** from §1.3,
since that table's own time axis (`week_start_date`) is secondary to *which run* is selected.

Every KPI card is paired with a small text label stating the **measure name, its unit, and a
one-line definition** — a bare number satisfies none of "KPI definitions and units are visible."
The wording below is what that label says; it is copied from `docs/BUSINESS_RULES.md` §4, not
reworded, so the report never drifts from the definition already agreed there.

### 3.1 Page "Shortage & Coverage" (Decisions 1, 3, 6)

| Visual | Measure(s) | Label text under/beside it |
|---|---|---|
| KPI card | `Weeks of Cover` | "Weeks of Cover (weeks) — on-hand ÷ average weekly demand, forward-looking only, capped at 13" |
| KPI card | `SKUs - No Forward Demand` | "SKUs with no forward demand (count) — weeks_of_cover is not meaningful for these, shown separately so the average above is not read as if it included them" |
| KPI card | `SKUs With Shortage` | "SKUs with a projected shortage within 13 weeks (count)" |
| Text box next to it | — | "117 of 120 SKUs typically show a shortage in this sample — demand and inventory are generated independently (`data/sample/README.md`), this is a data-generation property, not a dashboard fault." |
| Table | `product_id`, `family`, `First Shortage Week`, `Projected Shortage (Units)` | Sorted by `First Shortage Week` ascending — answers Decision 1 ("which SKUs, in which week") directly as a row-level list, not only as an aggregate. |
| Bar chart | `Weeks of Cover` by `family` | "Average weeks of cover by family — **not** compared against a numeric service-level target: `ASM-08`'s 95%/98% target is a registered assumption that no part of this pipeline currently converts into a weeks-of-cover threshold or stores in the database. Decision 6 is therefore only partially answered — see limitation below." |
| Line chart | `Projected Shortage (Units)` by `Week Label`, one line per selected SKU | Answers "ties up cash" (Decision 3) only in **pieces**, per §1.6 — no currency conversion exists anywhere in `docs/DATA_DICTIONARY.md`. |

**Decision 2 is not on this page, deliberately** — a text box states why: "Suggested purchase
order quantity and date are computed in `replenishment.py` (P1.5) but not persisted to any table,
so this report cannot show them. See the P1.5 session log." Leaving the card out would look like an
oversight; the text box makes it a stated limitation instead.

### 3.2 Page "Capacity" (Decision 4)

| Visual | Measure(s) | Label text |
|---|---|---|
| KPI card | `Capacity Utilisation %` | "Capacity utilisation (%) — planned load ÷ available capacity, **not capped at 100%** so overload is visible rather than smoothed" |
| Column chart | `Capacity Utilisation %` by `Week Label`, split by `family` | A horizontal reference line at 100% (Power BI constant line, not a measure) makes overload visually obvious without needing to read exact numbers. |
| Table | `family`, `week_start_date`, `available_capacity_units`, `planned_load_units`, `Capacity Utilisation %` | Row-level detail behind the chart, filterable by the same family/week slicers — this is what makes the chart's claim checkable on the same page. |

No `planning_origin_date` element on this page — `fct_capacity` does not carry that column, so the
§1.3 slicer would filter nothing and must not be added just for layout consistency.

### 3.3 Page "Supplier Delivery (OTIF)" (Decision 5)

| Visual | Measure(s) | Label text |
|---|---|---|
| KPI card | `Supplier OTIF %` | "On-time-in-full rate (%) — lines received exactly on the promised date ÷ lines due, 0-day tolerance (`ASM-06`)" |
| Bar chart | `Supplier OTIF %` by `supplier_name` (from `dim_supplier`), sorted ascending | Ranks suppliers from worst to best — directly answers "which ones degrade the plan." |
| KPI card pair | `OTIF Lines`, `Lines Due` | Shown next to the rate so a viewer can see *how many* lines a percentage is based on — a 100% OTIF rate on 2 lines due reads very differently from one on 80. |

A product/SKU slicer is still present (per the shared layout rule above) even though OTIF is a
supplier-level question, because `fct_purchase_order_line` carries `product_id` and a buyer may
want "this supplier's OTIF, for this product family only."

### 3.4 What was verified today (2026-11-17), and what is still open

The four validation queries from §2 were run against the local dev database
(`supply_planning_lab`, port 5433) exactly as written, no edits:

| Measure | Validation query result | Matches session log? |
|---|---|---|
| `Weeks of Cover` (origin `2026-05-04`) | 120 rows, avg `1.98`, `0` with `no_forward_demand` | New number, first time computed at this precision — logged here, not previously stated |
| `SKUs With Shortage` | `117` | Yes — P1.5 session log, "117 of 120" |
| `Capacity Utilisation %` (`FOOT`, `2026-06-15`) | `122.3` | Yes — exact match |
| `Supplier OTIF %` (overall) | `71 / 215 = 33.0%` | Yes — "roughly 33% overall" |

This confirms the **SQL side** of every formula in §2 is correct and stable against the current
sample data. It does **not** confirm the **DAX side** — that the measures in §2, typed into an
actual Power BI model, return these same numbers under the same filters. That half of "important
measures reconcile to SQL" can only be checked once the `.pbix` exists (§4).

---

## 4. Build checklist — to run on a Windows PC with Power BI Desktop

Nothing below has been executed yet. This is the exact sequence to follow, in order, so finishing
P1.6 later does not require re-deriving the model from scratch:

1. **Install Power BI Desktop**, then **Get Data → PostgreSQL database** per §1.5
   (`localhost:5433` or the reachable dev-DB host, database `supply_planning_lab`, schema
   `analytics` only). Import mode, not DirectQuery (§1.5's reasoning).
2. **Import exactly the 8 tables listed in §1.1** — not the two views; do not let Power BI
   auto-suggest additional tables.
3. **Build the 10 relationships in §1.2** exactly as listed, including which columns get **no**
   relationship (`order_date`, `actual_receipt_date`, `planning_origin_date`).
4. **Mark `dim_calendar` as the date table** (§1.4), add the `Week Label` calculated column.
5. **Type in the 9 DAX measures from §2**, verbatim — do not retype the formula from memory,
   copy from this document so a transcription slip cannot silently diverge from the validated SQL.
6. **Build the 3 pages from §3.1–§3.3**, including every disclosure text box — they are part of
   the acceptance criteria, not optional polish.
7. **Reconcile each measure**: for the same filter context as each §2 validation query (same
   `planning_origin_date`, same family/product/week selection), compare the DAX card's number to
   the SQL result already confirmed in §3.4. Record the actual comparison — number vs number —
   in `docs/SESSION_LOG.md`, not just "looks right."
8. **Screenshot every page** (with a non-empty filter selection on at least one, to prove filtering
   works, not just the default view) and save under `docs/screenshots/power_bi/`.
9. **Save the `.pbix`** — do not commit it if it embeds credentials; if Power BI prompts to store
   the connection password, decline and rely on the Windows PC's saved credential instead, same
   least-privilege rule as `.env`.
10. Update `docs/POWER_BI_REPORT.md` §3.4's table with the real DAX-vs-SQL comparison, update
    `docs/SESSION_LOG.md` with a dated entry, and only then set P1.6 to `DONE` in
    `docs/ROADMAP.md`.
