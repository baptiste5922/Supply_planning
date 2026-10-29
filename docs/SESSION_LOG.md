# Session Log

Append one entry after each meaningful working session. Keep entries concise and factual.

## Template

### YYYY-MM-DD — Task ID and title
- **Goal:**
- **Implemented:**
- **Concepts learned:**
- **Checks run and actual results:**
- **Known limitations / decisions:**
- **Next task:**
- **Question I can now answer without AI:**

---

### 2026-10-14 — Context bundle created
- **Goal:** Establish project context, roadmap, teaching rules, specialist agents and reusable skills.
- **Implemented:** Initial Claude Code context files and project roadmap.
- **Concepts learned:** Not yet assessed; use the learning-first workflow during implementation.
- **Checks run and actual results:** Bundle creation only; no application code or project tests have been run.
- **Known limitations / decisions:** This is a planning scaffold, not a working application. Confirm local Claude Code support and adapt if the installed version differs.
- **Next task:** P0.1 — Define the fictional business and decisions.
- **Question I can now answer without AI:** What are the three portfolio projects and how do they support the target role?

### 2026-10-19 — P0.1 Business rules and P0.2 Repository and Python environment
- **Goal:** Define the business frame before any implementation, then make the repository
  versioned and reproducible.
- **Implemented:**
  - `docs/BUSINESS_RULES.md`: fictional company Alpiflow (trail running), 4 product families,
    grain SKU x week, 13-week horizon, single warehouse `WH-01`, unit = piece. 6 business
    decisions, 4 KPI definitions (weeks of cover, projected shortage, capacity utilisation,
    supplier OTIF), 10 labelled assumptions `ASM-01..ASM-10`, 6 open questions.
  - `requirements.txt` (pandas, SQLAlchemy, psycopg[binary], python-dotenv, pytest),
    `src/supply_planning/` package with environment-based configuration loading,
    `pytest.ini`, `tests/test_smoke.py`.
  - `.gitignore` fix: the `*.csv` rule was hiding the `data/sample/` fixtures that P1.3 must
    version; added a negation for `data/sample/**`.
  - `README.md`: added a `Getting started` section with the reproducible install procedure.
  - Repository initialised with git (it was not versioned at all before today).
- **Concepts learned:** choice of planning grain (day-of-week noise, intermittent demand),
  projected inventory balance equation, the rescheduled-promise-date pitfall in supplier OTIF,
  why configuration must fail loudly rather than fall back to defaults.
- **Checks run and actual results:**
  - `python -m pytest` -> `5 passed` (run twice: project venv, and a freshly created venv
    built only from the README instructions).
  - `git add --dry-run` confirmed `data/sample/*.csv` is tracked while `data/raw/*.csv` stays
    ignored, and that neither `.env` nor `.venv/` is staged.
  - No database connection was tested; PostgreSQL is not used yet.
- **Known limitations / decisions:** the numeric assumptions (lead times, capacity, safety
  stock, service targets) are synthetic and not validated by a domain expert. Stockout-censored
  sales remain an open question and must be settled before P1.3. Python 3.14 is the only
  interpreter available locally; all wheels installed without compilation.
- **Next task:** P0.3 — document the data flow in `docs/ARCHITECTURE.md`.
- **Question I can now answer without AI:** why plan at SKU x week rather than SKU x day, and
  what the projected inventory balance equation computes.

### 2026-10-20 — P0.3 Learn the data flow
- **Goal:** document, before any schema or code, where each number comes from and which system
  owns it.
- **Implemented:**
  - `docs/ARCHITECTURE.md` rewritten from the generic scaffold into an Alpiflow-specific
    document: Phase 1-2 flow diagram (CSV/generator -> Python extract/validate/transform ->
    PostgreSQL `raw`/`clean`/`analytics` -> Power BI), a separate Phase 3 diagram showing the
    Odoo test instance as an **optional, read-only** operational source, a component
    responsibility table with an explicit "does not do" column, the three-schema layering with
    naming conventions, a **source-of-truth table per data domain** for Phases 1-2 and 3,
    execution/reproducibility conventions, repository layout, and an out-of-scope list.
  - `docs/BUSINESS_RULES.md`: open question "Source of truth per field" closed for Phases 1-2
    and marked "proposed" for Phase 3; header annotated with the amendment.
  - `docs/ROADMAP.md`: P0.3 marked DONE.
- **Concepts learned:** why a one-way data flow is what makes a result reproducible; why `raw`
  must be kept even though it is messy (it separates "wrong at source" from "broken by my code");
  the difference in purpose between `clean` (is this row trustworthy) and `analytics` (is this row
  shaped for a question); the rule "one field, one producer" as the way conflicts are resolved;
  why a labelled assumption is a legitimate source of truth while a hidden default is not.
- **Checks run and actual results:**
  - `python -m pytest` -> `17 passed` (documentation-only change, run to confirm no regression).
  - Acceptance criteria re-read against the file: the three criteria of P0.3 are each covered by
    §1.1, §1.2 and §2 + §4 respectively.
  - No database or Odoo connection was attempted; PostgreSQL is still unused.
- **Known limitations / decisions:** the Phase 3 source-of-truth column is a proposal, not a
  verified decision — it assumes Odoo demo data is credible enough to replace the synthetic
  catalogue, stock and purchase orders, which can only be confirmed in P3.5. The table names
  listed for the `analytics` schema are an intention, not a committed schema; P1.2 may rename or
  drop some. No orchestrator, no container, no write-back to Odoo in v1, by explicit decision.
- **Next task:** P1.1 — define the data grain, data dictionary and field-level rules
  (`docs/DATA_DICTIONARY.md`), which must settle the remaining open questions that block P1.3
  (stockout censoring, returns, end-of-life SKUs).
- **Question I can now answer without AI:** which system owns the on-hand stock figure, which
  system owns the projected shortage, and what to conclude when the two disagree.

### 2026-10-21 — P1.1 Data grain, dictionary and KPI rules
- **Goal:** turn the generic `docs/DATA_DICTIONARY.md` draft into a field-level, typed, keyed
  dictionary that P1.2 can translate directly into `CREATE TABLE` statements, and close the
  remaining open question that explicitly blocked this task.
- **Implemented:**
  - `docs/DATA_DICTIONARY.md` rewritten: seven tables (`dim_product`, `dim_calendar`,
    `dim_supplier`, `fct_demand_actual`, `fct_inventory_snapshot`, `fct_purchase_order_line`,
    `fct_capacity`), each with grain stated in one sentence, PK/FK, types, units, and an explicit
    missing-data rule. `fct_demand_forecast` and `fct_planning_exception` deliberately left
    undefined — they are Phase 2 / P1.5 outputs, not source tables, and defining them now would
    mean guessing their shape.
  - `docs/BUSINESS_RULES.md`: closed the "e-commerce returns" open question (ignored in v1,
    documented as a limitation on `fct_demand_actual`); added `ASM-11` (capacity split by family)
    to resolve a gap found while writing the capacity table — `ASM-05` only gave one warehouse-wide
    total, but the KPI in §4.3 is defined at family grain.
  - `docs/ROADMAP.md`: P1.1 marked DONE.
- **Concepts learned:** grain can legitimately differ between the `clean` and `analytics` layers
  (channel-level vs SKU-week aggregated) as long as it is documented; `NULL` vs `0` vs an absent
  row are three distinct, meaningful states (`received_qty`, missing SKU-weeks); why lead time and
  MOQ live in configuration keyed by family rather than on the supplier dimension (one source of
  truth per fact); why the two purchase-order cancellation reasons must stay distinct values
  rather than collapsing into one `cancelled` status, because the OTIF KPI treats them differently.
- **Checks run and actual results:** `python -m pytest` → `17 passed` (documentation-only change,
  run to confirm no regression). No database exists yet to check the dictionary against.
- **Known limitations / decisions:** `ASM-11`'s family split (35/25/25/15%) is an invented,
  labelled, configurable percentage, not a measured warehouse capability — it will over-report
  family-level capacity overload compared with a warehouse that can reallocate pickers across
  families within a week. Returns, stockout censoring, promotions and collection end-of-life
  remain open and are deferred to the tasks that explicitly depend on them (P1.2, P1.3, P2.3).
- **Next task:** P1.2 — design the PostgreSQL schema (`sql/`) directly from this dictionary:
  primary/foreign keys, `CHECK` constraints on `family` and `status`, and confirmation that the
  schema can be created on a fresh development database.
- **Question I can now answer without AI:** why `fct_purchase_order_line.promised_receipt_date`
  must be immutable once a purchase order is confirmed, and why `cancelled_by_alpiflow` and
  `cancelled_by_supplier` cannot be merged into a single `cancelled` status.

### 2026-10-29 — P1.2 PostgreSQL schema
- **Goal:** translate `docs/DATA_DICTIONARY.md` directly into versioned SQL DDL for the three
  schemas, and prove — not just assert — that it creates cleanly and that its constraints work.
- **Implemented:**
  - `sql/001_create_schemas.sql`, `sql/002_raw_tables.sql`, `sql/003_clean_tables.sql`,
    `sql/004_analytics_tables.sql`: `raw` (7 loose-typed tables + ingestion metadata, no PK on
    business keys — append-only), `clean` (7 typed/keyed tables, plain names, PK/FK/CHECK exactly
    per the dictionary), `analytics` (same 7 tables, `dim_`/`fct_` prefixes). Decision: `clean` and
    `analytics` share the same shape for v1 — no transformation exists yet to justify a
    difference; the schema boundary is there so one can later diverge without touching the other.
  - `README.md`: added the dev-database setup step (createuser/createdb/`psql -f sql/*.sql`) and
    corrected a stale test count (`5 passed` → `17 passed`, left over from P0.1).
- **Concepts learned:** why a weekly fact's `week_start_date` can `REFERENCES calendar(calendar_date)`
  directly — the Monday of every week is itself a row in the daily calendar table, so no separate
  "weeks" table is needed; why some documented rules (`unit_of_measure`'s constancy, `site_id`'s
  single current value, `promised_receipt_date`'s immutability) are deliberately **not** encoded as
  `CHECK` constraints — a `CHECK` would force a schema migration exactly when the documented
  future extension (multi-unit, multi-site) happens, which defeats the column's stated purpose;
  why `raw` has no uniqueness on business keys (append-only, dedup happens on the way to `clean`).
- **Checks run and actual results:**
  - Started an isolated Homebrew PostgreSQL 18 on port 5433 (the machine already runs a system
    PostgreSQL on 5432 for other work, managed by pgAdmin — left untouched on purpose).
  - `createuser supply_planning_app` (no superuser/createdb attributes) + `createdb
    supply_planning_lab`; ran the four SQL files in order with `psql -v ON_ERROR_STOP=1` →
    21/21 `CREATE TABLE`/`CREATE SCHEMA` statements succeeded, 0 errors.
  - Re-ran the same four files against the already-created schema → all `NOTICE: ... already
    exists, skipping`, 0 errors (idempotency check).
  - Inserted valid rows into `clean.product`/`clean.calendar`/`clean.demand_actual`, then
    deliberately tried three invalid inserts: a `FOOT` product with no `size` (rejected by
    `product_size_matches_family`), an unknown `family` value (rejected by the `family` `CHECK`),
    and a `demand_actual` row pointing at a non-existent `product_id` (rejected by the foreign
    key) — all three failed exactly as designed.
  - Dropped and recreated `supply_planning_lab` from scratch, re-ran the four files once more →
    clean database, 7 tables in each of `raw`/`clean`/`analytics`, 0 errors. This is the state the
    database is left in.
  - `python -m pytest` → `17 passed` (no application code changed; regression check only).
- **Known limitations / decisions:** `clean` and `analytics` are currently identical in shape —
  acceptable for v1 per `docs/ARCHITECTURE.md` ("no layer added just to look sophisticated"), but
  P1.4/P1.5 may reveal a real transformation that belongs only in `analytics`. `raw` table shapes
  are a forecast of what P1.3's generator will produce, typed loosely in TEXT; if the generator's
  actual columns differ, `sql/002_raw_tables.sql` will need a follow-up migration file, not an edit
  to this one. The local `.env` points at a project-only PostgreSQL instance on port 5433,
  deliberately separate from the pre-existing system PostgreSQL on this machine.
- **Next task:** P1.3 — build the deterministic synthetic dataset (generator + `data/sample/`
  fixtures), which will also settle the still-open stockout-censoring question before anything is
  generated.
- **Question I can now answer without AI:** why `clean.calendar` doesn't need a separate "weeks"
  table for a weekly fact to reference, and why three of the dictionary's documented rules are
  deliberately left unenforced by a `CHECK` constraint.
