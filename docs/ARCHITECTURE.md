# Architecture — Alpiflow Supply Planning Portfolio

> **Disclaimer.** Alpiflow is a **fictional** company and every dataset in this portfolio is
> **synthetic**. See `docs/BUSINESS_RULES.md` for the business frame and the assumptions register.

- **Status:** v1 — P0.3
- **Date:** 2026-10-20
- **Scope:** data flow, component responsibilities and source-of-truth decisions for the three
  portfolio projects.

This document answers three questions: **where does a number come from**, **who is allowed to
produce it**, and **who wins when two systems disagree**. It deliberately contains no business
figure — thresholds, lead times and KPI formulas live in `docs/BUSINESS_RULES.md` only.

---

## 1. Data flow

### 1.1 Phases 1 and 2 — the portfolio runs without any ERP

```text
  SOURCES                    PROCESSING                 STORAGE                 CONSUMPTION
  (synthetic)                (Python)                   (PostgreSQL)

┌──────────────────┐
│ data/sample/*.csv│
│  products        │      ┌─────────────────┐      ┌───────────────────┐
│  calendar        │─────>│ 1. extract      │─────>│ schema  raw       │
│  sales history   │      │    + metadata   │      │ source-shaped,    │
│  inventory snap. │      └─────────────────┘      │ append-only       │
│  purchase orders │               │               └─────────┬─────────┘
│  suppliers       │               │                         │
│  capacity        │               v                         v
└──────────────────┘      ┌─────────────────┐      ┌───────────────────┐
         ^                │ 2. validate     │      │ schema  clean     │
         │                │    + quality    │─────>│ typed, keyed,     │
┌──────────────────┐      │    report       │      │ deduplicated      │
│ generator        │      └─────────────────┘      └─────────┬─────────┘
│ (deterministic,  │               │                         │
│  seeded) P1.3    │               v                         v
└──────────────────┘      ┌─────────────────┐      ┌───────────────────┐     ┌──────────────┐
                          │ 3. transform    │      │ schema  analytics │     │  Power BI    │
                          │    facts/dims   │─────>│ star schema +     │────>│  Control     │
                          └─────────────────┘      │ planning results  │     │  Tower       │
                                                   └─────────┬─────────┘     └──────────────┘
                          ┌─────────────────┐                │                      ^
                          │ 4. planning     │<───────────────┘                      │
                          │    calculations │ reads clean/analytics                 │
                          │    (P1.5)       │────────────────┐                      │
                          └─────────────────┘                │                      │
                                                             v                      │
                          ┌─────────────────┐      ┌───────────────────┐            │
                          │ 5. forecasting  │      │ analytics.        │            │
                          │    experiments  │─────>│ fct_demand_       │────────────┘
                          │    (Phase 2)    │      │ forecast          │
                          └─────────────────┘      └───────────────────┘
```

Read the diagram as a one-way street: **nothing flows right to left.** Power BI never writes to
PostgreSQL, PostgreSQL never writes back to a CSV source, and the forecasting notebooks never
mutate `clean`. A one-way flow is what makes a result reproducible — you can always rebuild every
layer downstream of a source by re-running the pipeline.

### 1.2 Phase 3 — Odoo added as an **optional** operational source

```text
┌────────────────────────────────────────┐
│  Odoo test instance (operational ERP)  │   <-- OPTIONAL, Phase 3 only
│  synthetic records, test database      │       Phases 1-2 run without it
│                                        │
│  product.product   stock.quant         │
│  purchase.order    purchase.order.line │
└───────────────────┬────────────────────┘
                    │  READ ONLY
                    │  supported API (XML-RPC / JSON-RPC), paginated
                    v
          ┌───────────────────┐
          │ Python extractor  │  credentials from .env, never committed
          │ (P3.5)            │
          └─────────┬─────────┘
                    v
          ┌───────────────────┐
          │ schema  raw       │   same raw -> clean -> analytics path as 1.1
          │ (odoo_* tables)   │   Odoo records land next to CSV records,
          └───────────────────┘   tagged by source_system
```

Three constraints are structural, not stylistic:

- **Odoo is read-only for this portfolio.** We never `INSERT` into its internal tables and never
  write planning results back into it. The APS simulation (P3.6) proposes orders; a human would
  key them into the ERP.
- **Odoo is optional.** Phases 1 and 2 must stay runnable on a machine with no Odoo instance. The
  demo cannot depend on a server that may be down during an interview.
- **Odoo records land in `raw` like any other source**, tagged with `source_system = 'odoo'`. The
  downstream layers do not care where a row came from; that is the point of having a `raw` layer.

---

## 2. Component responsibilities

The "does not" column matters as much as the "does" column: most architecture failures are a
component quietly taking on a job that belongs to another.

| Component | Does | Does **not** do |
|---|---|---|
| **Sources** (`data/sample/`, generator, later Odoo) | Hold the facts: catalogue, calendar, sales, stock snapshots, purchase orders, suppliers, capacity | Contain any derived or computed value |
| **Python — ingestion** (`src/supply_planning/`) | Extract, type, validate, deduplicate, log row counts, emit a data-quality report | Silently drop or repair an invalid row; invent a missing lead time |
| **Python — planning logic** | Compute the projected inventory recurrence, coverage, shortages, capacity load, OTIF | Hard-code a threshold — every assumption comes from configuration |
| **Python — forecasting** (Phase 2) | Train, evaluate chronologically, write forecasts with `model_version` and `forecast_origin` | Overwrite actuals; reuse future information |
| **PostgreSQL** | Persist the three layers, enforce keys/constraints, serve queryable data products | Host business logic in triggers or stored procedures (logic stays in versioned Python/SQL files) |
| **Power BI** | Filter, aggregate, present; hold presentation-level measures only | Re-implement a KPI formula that SQL already computes — it must reconcile, not reinterpret |
| **Odoo** (Phase 3) | Play the operational system of record for transactions | Receive any write from this project |
| **Tests** (`tests/`) | Verify schema, ingestion failure paths, planning arithmetic against hand-calculated examples | Replace the manual verification procedures documented per task |

---

## 3. The three PostgreSQL schemas

One database (`supply_planning_lab`), three schemas. Not three databases: a single connection
keeps the demo simple, and schemas already give us the separation we need.

| Schema | Grain | Contents | Rebuildable? |
|---|---|---|---|
| `raw` | Exactly the source's grain | Source-shaped rows, loose types, plus ingestion metadata: `source_system`, `source_file`, `extracted_at`, `load_id` | No — this is the landing zone; it is what we keep |
| `clean` | One documented grain per table, enforced by a primary key | Validated types, canonical keys, units normalised to pieces, dates as plain dates, duplicates removed | Yes, from `raw` |
| `analytics` | Star-schema facts and dimensions, plus planning outputs | `dim_product`, `dim_calendar`, `dim_supplier`, `fct_demand_actual`, `fct_inventory_snapshot`, `fct_purchase_order_line`, `fct_capacity`, `fct_demand_forecast`, `fct_planning_exception` | Yes, from `clean` |

**Why keep `raw` at all**, given it is messy by design? Because a data-quality question is always
"was the value wrong at the source, or did my code break it?" Without `raw` you cannot answer that,
and without `extracted_at` you cannot reproduce a result someone saw last week.

**Why `clean` is separate from `analytics`:** `clean` answers "is this row trustworthy", `analytics`
answers "is this row shaped for a question". Mixing them produces tables that are hard to validate
and hard to query. The first version of each table stays deliberately simple — no layer is added
just to look sophisticated.

### Naming conventions

- `snake_case` everywhere, singular column names, plural never.
- Table prefixes in `analytics`: `dim_`, `fct_`.
- A date column is named `*_date`; a week column is always `week_start_date` (ISO Monday, per
  `docs/BUSINESS_RULES.md` §3).
- Quantities carry their unit in the name only when ambiguity is possible (`*_units`, `*_pct`).
- Nothing is named `temp_`, `new_` or `final_`. Versioning is git's job.

---

## 4. Source-of-truth decisions

The rule that resolves every conflict: **a field has exactly one producer.** Everything else reads
a copy.

| Data domain | Phases 1–2 (source of truth) | Phase 3 (source of truth) | Conflict rule |
|---|---|---|---|
| Product catalogue, families, SKU attributes | `data/sample/products.csv` | **Odoo** `product.product` | Odoo wins. The ERP is where a product is created operationally. |
| Calendar / ISO weeks | Generated in Python, deterministic | unchanged | Never sourced from an ERP; it is a derived dimension. |
| Sales / demand actuals | Synthetic generator (P1.3) | **Odoo** sales documents if modelled, else generator | The ERP wins where it exists; the generator is explicitly labelled synthetic. |
| On-hand and allocated stock | `data/sample/inventory_snapshot.csv` | **Odoo** `stock.quant` | Odoo wins. Physical stock is an operational fact; analytics must never "correct" it. |
| Purchase orders, promised and actual receipt dates | `data/sample/purchase_orders.csv` | **Odoo** `purchase.order.line` | Odoo wins. |
| Supplier lead time, MOQ | `docs/BUSINESS_RULES.md` assumptions, exposed in configuration | Configuration still wins unless Odoo holds a maintained value | Documented as an assumption (`ASM-04`, `ASM-07`); configuration is the producer because Odoo demo data has no credible lead times. |
| Warehouse capacity | Configuration (`ASM-05`) | unchanged | Not an ERP concept here; stays an explicit assumption. |
| Safety stock, service targets, tolerances | Configuration (`ASM-03`, `ASM-06`, `ASM-08`) | unchanged | Planning parameters belong to the planning system, not to the ERP. |
| **Demand forecast** | **This project** (`analytics.fct_demand_forecast`) | unchanged | Produced here; never pushed to Odoo. |
| **Projected inventory, coverage, shortages, exceptions** | **This project** (`analytics`) | unchanged | Derived values. If they disagree with a source, the source is right and our logic is wrong. |
| KPI values shown on a dashboard | SQL in `analytics` | unchanged | Power BI reconciles to SQL. A divergence is a Power BI bug, by definition (P1.6 acceptance criterion). |

Two consequences worth stating explicitly:

1. **Operational facts flow one way: ERP → analytics.** Analytics owns only what it derives.
2. **An assumption is a legitimate source of truth**, provided it is labelled, configurable and
   traceable to an `ASM-xx` identifier. The failure mode is not "we invented a lead time", it is
   "we invented a lead time and hid it in the code".

This closes the Phase 1–2 half of the open question *"Source of truth per field"* in
`docs/BUSINESS_RULES.md` §6. The Phase 3 column above is a **proposed** decision: it must be
re-confirmed in P3.5 once the real shape of the Odoo test data is known, in particular whether
Odoo demo records are credible enough to replace the synthetic history.

---

## 5. Execution and reproducibility conventions

- **Configuration via environment.** Connection parameters come from `.env` (see `.env.example`);
  `src/supply_planning/config.py` raises rather than falling back to a default, so a run can never
  silently hit the wrong database.
- **Business parameters via configuration, not code.** Every `ASM-xx` value becomes a configuration
  entry, so a reviewer can change a lead time without editing logic.
- **Idempotent loads.** Re-running an ingestion must not duplicate rows. Each load carries a
  `load_id`, and `clean` tables have a real primary key — the duplicate is rejected by a constraint,
  not by a convention.
- **Deterministic generation.** The synthetic generator is seeded; the same seed produces the same
  dataset (P1.3 acceptance criterion).
- **Invalid rows are reported, never deleted.** Ingestion writes a data-quality report; a SKU with
  a missing lead time appears there with a reason code instead of being computed with a guess.
- **Notebooks explore, modules compute.** `notebooks/` is for investigation and may be messy;
  anything reused moves into `src/supply_planning/` and gets a test.
- **Secrets never committed.** `.env`, credentials and raw private exports are excluded by
  `.gitignore`; only `data/sample/` fixtures are versioned.

---

## 6. Repository layout

| Path | Role |
|---|---|
| `src/supply_planning/` | Importable modules: configuration, ingestion, validation, planning calculations, forecasting helpers |
| `sql/` | Versioned, ordered DDL and analytical queries (P1.2) |
| `data/raw/` | Local, git-ignored landing area for downloaded or extracted files |
| `data/sample/` | Small, versioned, deliberately synthetic fixtures used by tests and the demo |
| `data/processed/` | Git-ignored intermediate outputs |
| `notebooks/` | Exploration only |
| `tests/` | Automated checks |
| `docs/` | Business rules, data dictionary, architecture, roadmap, session log, requirements |

---

## 7. Deliberately out of scope

Listed so that their absence reads as a decision rather than an omission:

- No orchestrator (Airflow, Dagster, dbt) in v1 — the pipeline is a handful of ordered Python
  entry points. Orchestration is added only when the dependency graph stops fitting in one page.
- No cloud deployment, no container cluster, no streaming. Local PostgreSQL, run on demand.
- No write-back to Odoo, no production APS optimiser; the APS layer is a labelled rules-based
  simulation.
- No deep learning in Phase 2 before a seasonal-naïve baseline has been beaten.
- No multi-site or multi-currency model — a single `site_id` column exists so the extension stays
  cheap, but only one value is used (`WH-01`).
