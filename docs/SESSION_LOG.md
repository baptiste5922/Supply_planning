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

### 2026-11-01 — P1.3 Synthetic dataset generator
- **Goal:** build a deterministic, seeded generator for all seven P1.3 tables, settle the
  still-open "stockout-censored sales" question first, and produce a small committed fixture
  under `data/sample/` with documented edge cases for P1.4/P1.5 to test against.
- **Implemented:**
  - Decision (user-confirmed): `was_stocked_out` is added to `fct_demand_actual`. Closed in
    `docs/BUSINESS_RULES.md` §6 and `docs/DATA_DICTIONARY.md` §4.
  - `sql/005_add_stockout_flag.sql`: a follow-up migration (not an edit to `002`/`003`/`004`, per
    the decision already recorded when those files were written) adding the column to
    `raw`/`clean`/`analytics`, `NOT NULL` with the `DEFAULT` dropped immediately after the `ALTER`.
  - `src/supply_planning/generator/`: `assumptions.py` (typed `ASM-03/04/05/06/07/09/11` register,
    validated at construction — e.g. `capacity_share` must sum to 1.0), `calendar.py`, `product.py`,
    `supplier.py`, `demand.py`, `inventory.py`, `purchase_order.py`, `capacity.py`, `run.py`
    (orchestrator + raw-shaped CSV writer).
  - `scripts/generate_sample_data.py`: CLI with a `sample` preset (small, fixed window, committed)
    and a `full` preset (realistic ~120-SKU/3-year volume, gitignored under `data/raw/synthetic/`).
  - `data/sample/*.csv` (120 products, 6 suppliers, 30 weeks of demand/inventory/capacity, 240
    purchase-order lines) + `data/sample/README.md` documenting five deliberate edge cases by exact
    key (missing SKU-week, a genuine zero-demand run, negative available stock, a missing promised
    receipt date, one overloaded family-week) and the full OTIF/status rotation in purchase orders.
  - `tests/test_generator.py` (26 tests): determinism per table and end-to-end, every documented
    edge case asserted by exact key, grain/shape invariants (FOOT has `size`, others don't; qty
    fields never negative).
  - `README.md`: step 5 expected count corrected (`17` → `43` passed); added an optional step 6 to
    regenerate the sample dataset.
- **Concepts learned:** why a pure function of `(seed, start_date, end_date, assumptions)` — no
  hidden `date.today()` inside — is what "reproducible" actually requires, and why the committed
  fixture therefore uses a *frozen* window rather than a wall-clock-relative one; why a malformed
  source value (`promised_receipt_date = None`) can only be represented in `raw` and not in `clean`,
  because `clean`'s `NOT NULL` constraint would reject it — the generator models that by typing the
  field `date | None` only at the raw-shaped dataclass level; why a fixed, index-based case rotation
  (not pure randomness) is what actually *guarantees* every status/OTIF outcome appears, rather than
  hoping a random draw hits all six eventually.
- **Checks run and actual results:**
  - `python -m pytest` → `43 passed` (26 new generator tests + 17 pre-existing smoke tests).
  - Ran `scripts/generate_sample_data.py --preset sample` twice to a scratch directory and diffed
    every output file against the committed `data/sample/*.csv`, excluding the `extracted_at`/
    `load_id` metadata columns → byte-identical on all seven files, confirming reproducibility
    directly rather than only through the determinism unit tests.
  - Applied `sql/005_add_stockout_flag.sql` against the dev database (`supply_planning_lab`, port
    5433, left running from P1.2) after the four `sql/00[1-4]*.sql` files → 0 errors; re-ran it a
    second time → `NOTICE: ... already exists, skipping` on every statement, 0 errors (idempotency
    check). `\d` confirms `was_stocked_out boolean not null`, no default, on `clean.demand_actual`
    and `analytics.fct_demand_actual`, and `was_stocked_out text` (nullable) on `raw.demand_actual`.
- **Known limitations / decisions:** demand and inventory are generated independently per
  product-week (scaled by family magnitude/safety-stock assumptions), not by simulating the
  demand → receipt → stock recurrence end-to-end — P1.5 validates that recurrence by hand on its
  own small example instead. Purchase-order volume is a fixed 2 lines/SKU, not a time-phased
  reorder simulation — a deliberate scope cut for a "small sample fixture", not a production-volume
  ordering model. The exact seasonal ISO-week ranges implementing `ASM-09`'s qualitative description
  are this generator's own interpretation, disclosed in `assumptions.py`'s comments, not a new
  registered assumption.
- **Next task:** P1.4 — implement ingestion and quality checks (`src/`) against `data/sample/`:
  logged row counts, invalid-record reporting (not silent dropping), duplicate/missing-key checks,
  and at least one automated test covering a failure case. The five documented edge cases above are
  exactly what those checks must catch.
- **Question I can now answer without AI:** why `promised_receipt_date` can be `NULL` in `raw` but
  never in `clean`, and why the fixture's date window is hard-coded rather than computed from
  "today".

### 2026-11-01 — P1.4 Ingestion and quality checks
- **Goal:** build the `raw -> clean -> analytics` ingestion pipeline (docs/ARCHITECTURE.md §1) for
  all seven tables, implementing each table's missing-data rule from `docs/DATA_DICTIONARY.md`
  exactly, and verify it against the five edge cases P1.3 deliberately built into `data/sample/`.
- **Implemented:**
  - `src/supply_planning/ingestion/quality.py`: `QualityIssue`/`QualityReport`, formalising three
    distinct outcomes a row can have - `REJECTED` (excluded from `clean`), `FLAGGED` (loaded *and*
    reported - a valid but noteworthy fact), `MISSING` (no row to reject; the absence itself is the
    defect, found by comparing loaded keys against the batch's own expected grid).
  - `validators.py`: small parsers (`parse_int`, `parse_date`, `parse_bool`, ...) that return
    `(value, error)` instead of raising, so a bad row is reported, never an unhandled exception.
  - `raw_loader.py` (CSV -> `raw`, append-only, stamps *this run's* `source_system`/`extracted_at`/
    `load_id` rather than trusting the file's own metadata columns), `db_writer.py` (generic
    `INSERT ... ON CONFLICT DO UPDATE` upsert, shared by `clean` and `analytics`), one module per
    table (`product.py` ... `capacity.py`) encoding each table's own rules, `analytics_loader.py`
    (straight `clean -> analytics` copy, same shape in v1), `run.py` (orchestrator: dimensions
    first, then facts, using the dimensions' own just-validated rows as the foreign-key lookup
    sets - no extra round trip to re-read what was just written).
  - `scripts/run_ingestion.py`: CLI, logs row counts per table and every quality issue.
  - **Bug fix (found while verifying against the real database, not part of the original plan):**
    `config.py`'s `sqlalchemy_url()` built an invalid URL for a Unix-socket `PGHOST` (`/tmp`) - a
    URL host component cannot contain `/`. P1.2 never hit this because it only ever connected via
    the `psql` CLI (`-h /tmp`); P1.4 is the first Python code to open a real connection. Fixed by
    moving the socket path to a `host=` query parameter per libpq/psycopg convention, with a new
    test (`test_sqlalchemy_url_handles_a_unix_socket_host`).
  - `tests/test_ingestion.py` (44 tests): every documented edge case asserted by exact reason code
    and key, plus the explicit "a true zero must never be flagged" case.
  - `README.md`, `docs/ROADMAP.md` (P1.4 → DONE).
- **Concepts learned:** why "invalid" is not one concept - a row can be too broken to use
  (`REJECTED`), valid but alarming (`FLAGGED`, loaded anyway), or simply absent (`MISSING`, nothing
  to reject); why a missing `promised_receipt_date` is rejected regardless of `status`, even though
  `docs/DATA_DICTIONARY.md` discusses it in terms of three specific statuses - the schema's
  `NOT NULL` constraint has no such exception, so ingestion's "is this loadable" question is
  stricter than P1.5's later "which calculation excludes it" question; why `raw`'s own extract step
  must re-stamp ingestion metadata rather than trust a source file that happens to already have
  similarly-named columns.
- **Checks run and actual results:**
  - `python -m pytest` → `88 passed` (44 new ingestion tests + 26 generator + 18 smoke, one of
    which is new).
  - Ran `scripts/run_ingestion.py` against `data/sample/` on the dev database (`supply_planning_lab`,
    port 5433) after truncating every table → logged exactly 4 issues, matching
    `data/sample/README.md` by exact key: `missing_sku_week` (`APPAREL-001`/`2026-09-21`),
    `negative_available_stock` (`APPAREL-003`/`2026-03-02`), one rejected `purchase_order_line`
    (`PO-00001`, missing `promised_receipt_date`), `capacity_overload` (`FOOT`/`2026-06-15`). The
    zero-demand run (`APPAREL-002`) produced zero issues, confirmed by query.
  - Row counts after that run: `clean.product`/`analytics.dim_product` = 120, `clean.demand_actual`/
    `analytics.fct_demand_actual` = 3599 (3600 − 1 missing), `clean.purchase_order_line` = 239
    (240 − 1 rejected) - `clean` and `analytics` match exactly on every table, as expected from a
    straight copy.
  - Idempotency: re-ran the same ingestion a second time without truncating → `raw.product`
    120 → 240 and `raw.demand_actual` 3599 → 7198 (append, as designed), while `clean`/`analytics`
    row counts and content were unchanged (upsert, no duplicates). Then truncated and ran once more
    to leave the database in a single, clean load.
- **Known limitations / decisions:** `analytics` is populated as a plain copy of `clean` with no
  additional transformation, per the P1.2 decision that the two schemas share a shape in v1 - P1.5
  is where a real transformation (if any) would first appear. Duplicate keys within one batch are
  rejected *in full* (both/all copies), never resolved by picking a "first" row - consistent with
  "report, never guess", but means a genuine duplicate costs two good-looking rows, not one.
- **Next task:** P1.5 — calculate planning KPIs and exceptions (coverage, projected shortage,
  capacity utilisation, OTIF) from `analytics`, validated against a small hand-calculated example.
- **Question I can now answer without AI:** why a missing `promised_receipt_date` is rejected for
  every `status`, not just the three `docs/DATA_DICTIONARY.md` discusses, and why `raw` growing on
  every ingestion run while `clean`/`analytics` stay the same size is the idempotency property
  working correctly, not a bug.

### 2026-11-06 — P1.5 Planning KPIs and exceptions
- **Goal:** implement the projected-inventory recurrence (`docs/BUSINESS_RULES.md` §4, "the core
  calculation of the project"), weeks of cover, and replenishment suggestions, validated against a
  hand-calculated 3-week example (mandatory acceptance criterion) and against the real `data/sample/`
  fixture through the full `raw -> clean -> analytics` pipeline built in P1.3/P1.4.
- **Implemented:**
  - Refactor (prerequisite): moved `assumptions.py` and `quality.py` out of `generator/`/
    `ingestion/` into `src/supply_planning/` directly, so `planning/` (new) and the two existing
    packages share one copy of each instead of planning reaching into generator's package.
  - `src/supply_planning/planning/`: `projected_inventory.py` (the `PI_t` recurrence;
    `MissingDemandDataError` instead of defaulting a missing week to zero), `coverage.py`
    (`weeks_of_cover`, capped at 13 with `no_forward_demand` on zero cumulative demand, never
    infinite/`None`), `replenishment.py` (suggests an order qty/date from MOQ and lead time;
    `MissingLeadTimeError` instead of defaulting a missing family), `run.py` (orchestrator: reads
    `analytics` via SQLAlchemy, computes per product, writes `analytics.fct_projected_inventory`).
  - `sql/006_planning_outputs.sql`: `analytics.fct_projected_inventory` (grain
    `planning_origin_date` × `product_id` × `week_start_date` — the origin is part of the key so
    two runs on two Mondays coexist) plus two views, `v_capacity_utilisation` and `v_supplier_otif`,
    computed directly from `fct_capacity`/`fct_purchase_order_line` with no new input data.
  - **Design decision, not in the original plan but needed once `fct_planning_exception` (the
    placeholder name in `docs/ARCHITECTURE.md`/`docs/DATA_DICTIONARY.md`) had to become a real
    table:** implemented as `fct_projected_inventory` holding every week (not only exceptions) plus
    the two views — an exception is a `WHERE` filter on existing numbers, never a second stored
    copy. Both docs updated to point at the real shape.
  - `scripts/run_planning.py`: CLI, default planning origin `2026-05-04` (a Monday inside
    `data/sample/`'s fixed window chosen so the 13-week horizon and the 8-week trailing-average
    window both stay inside the fixture's known dates).
  - `tests/test_planning.py` (12 tests): the mandatory hand-calculated example (`OH=100, SS=30`,
    3 weeks, verified line by line in the test's own comments, including the `PI == SS` boundary
    which is *not* a shortage), zero-demand coverage, missing-lead-time, and one infeasible-plan
    scenario (`docs/.claude/skills/supply-planning`'s "test at least one scenario with no feasible
    plan").
  - `README.md`, `docs/ROADMAP.md` (P1.5 → DONE), `docs/ARCHITECTURE.md` §3, `docs/DATA_DICTIONARY.md`
    (new §8, renumbered §9/§10).
- **Concepts learned:** why the planning origin has to be part of the output table's primary key
  (a re-run on a different Monday is a new fact, not a correction of the old one); why `PI == SS`
  must not count as a shortage (`shortage = max(0, SS - PI)` is exactly 0 there, and
  `first_shortage_week` uses that, not a separate `<=` check) - got this slightly wrong on a first
  mental pass and the hand example caught it; why "missing lead time" (`docs/BUSINESS_RULES.md`
  §4.2) only ever shows up as a *tested* defensive branch, not a real occurrence against this
  fixture - `Assumptions.lead_time_weeks` is validated complete for all four families at
  construction, so the real pipeline can never actually trigger it.
- **Checks run and actual results:**
  - `python -m pytest` → `100 passed` (12 new planning tests + 88 from P1.3/P1.4, including the
    refactor's import-path updates).
  - Applied `sql/006_planning_outputs.sql` to the dev database twice → `CREATE TABLE`/`CREATE VIEW`
    then `NOTICE: ... already exists, skipping`, 0 errors (idempotency check).
  - Ran `scripts/run_planning.py` (origin `2026-05-04`) against the already-ingested `data/sample/`
    data: `1680` rows written (`120` products × `14` rows), confirmed idempotent on a second run
    (same count, no growth - the table's primary key makes the upsert a true no-op on identical
    input). Spot-checked one SKU's full 14-row output by hand against the query result: every
    `PI_t` matched `previous_pi + receipts - demand` exactly.
  - Queried `analytics.v_capacity_utilisation`/`v_supplier_otif` directly: correctly surfaced the
    P1.3 `FOOT`/`2026-06-15` overload at `122.3%`, and an overall ~33% OTIF rate consistent with the
    generator's documented 3-success-out-of-10 status rotation (`data/sample/README.md`).
  - Of 120 products, 117 showed a projected shortage within the horizon and only 3 had a feasible
    replenishment suggestion - confirmed this is the already-documented P1.3 limitation showing
    through (demand and inventory are generated independently, not as a consistent simulation), not
    a P1.5 defect, by hand-verifying one SKU's numbers were internally arithmetically correct.
- **Known limitations / decisions:** demand for weeks "in the future" relative to the planning
  origin is read from `analytics.fct_demand_actual` (real synthetic actuals), not a forecast - a
  disclosed Phase-1 stand-in, replaced once Phase 2 exists. `safety_stock_units` is sized from the
  mean of the 8 weeks immediately before the origin - a generator-level interpretation of `ASM-03`'s
  "weeks of average demand" text, not a new registered assumption (disclosed in `planning/run.py`'s
  docstring, same pattern as P1.3's seasonality windows). Replenishment suggestions are not written
  anywhere (no `propose_purchase_order` output table) - P1.5's acceptance criteria only require the
  logic and its tests, not a persisted suggestion log.
- **Next task:** P1.6 — build the Power BI report on top of `analytics` (including
  `fct_projected_inventory` and the two new views), with product/time filtering and KPI definitions
  visible on the report itself.
- **Question I can now answer without AI:** why a projected inventory exactly equal to the safety
  stock is a warning boundary, not yet a shortage, and why 117 out of 120 SKUs showing an
  "infeasible" replenishment suggestion in this fixture is a known data-generation limitation, not
  a bug in the recurrence itself.

### 2026-11-17 — P1.6 Power BI report (specification + SQL validation, build still open)
- **Goal:** finish as much of P1.6 as is verifiable without Power BI Desktop itself, since it
  requires Windows and no Windows VM is available on this Mac right now; decided with the user to
  keep the documentation/validation work moving and leave an exact checklist for a Windows PC
  session later, rather than claiming the report is built when it is not.
- **Implemented:**
  - `docs/POWER_BI_REPORT.md` §3: page specification for the three report pages ("Shortage &
    Coverage", "Capacity", "Supplier Delivery (OTIF)"), each mapped to specific decisions from
    `docs/BUSINESS_RULES.md` §2, with the shared layout rules (synthetic-data banner, family/SKU
    slicers, `planning_origin_date` slicer where relevant) and the KPI-card label text copied
    verbatim from `docs/BUSINESS_RULES.md` §4 rather than reworded.
  - `docs/POWER_BI_REPORT.md` §4: a 10-step build checklist to run once Power BI Desktop is
    available, ending in updating §3.4's reconciliation table and only then setting P1.6 to DONE.
  - `docs/ROADMAP.md`: P1.6 moved `TODO` → `IN_PROGRESS` with the blocker stated explicitly.
- **Concepts learned:** Decision 6 ("coverage per family aligned with the defined service target")
  cannot actually be answered quantitatively by this report — `ASM-08` (the 95%/98% service-level
  target) is a registered assumption in `docs/BUSINESS_RULES.md` that no code anywhere converts
  into a stored number; grepping `src/` and `sql/` for `service_level`/`ASM-08` returns nothing.
  The honest move is to disclose that gap on the report page, not to invent a weeks-of-cover
  threshold that looks like it comes from `ASM-08` but doesn't.
- **Checks run and actual results:** ran the four §2 validation queries directly against the local
  dev database (`supply_planning_lab`, port 5433) with `psql`:
  - Weeks of Cover, origin `2026-05-04`, `weeks_ahead = 0`: 120 rows, average `1.98`, `0` rows with
    `no_forward_demand` — a new number, not previously stated in any session log.
  - SKUs with a projected shortage: `117` — matches the P1.5 session log's "117 of 120" exactly.
  - Capacity utilisation, `FOOT`/`2026-06-15`: `122.3%` — exact match to the P1.5 session log.
  - Supplier OTIF overall: `71 / 215 = 33.0%` — matches "roughly 33% overall".
  This confirms the SQL formulas in §2 are correct and stable; it does **not** confirm the DAX
  measures return the same numbers, since no `.pbix` exists yet to check.
- **Known limitations / decisions:** the `.pbix` file, the screenshots, and the DAX-vs-SQL
  reconciliation required by P1.6's acceptance criteria do not exist. Power BI Desktop is
  Windows-only; this Mac has no Windows VM and the user chose not to pay for Parallels to get one.
  Work will resume on a Windows PC using `docs/POWER_BI_REPORT.md` §4 as the exact script.
- **Next task:** execute `docs/POWER_BI_REPORT.md` §4 on a Windows PC: import the model, type the
  9 DAX measures, build the 3 pages, reconcile each measure against the SQL results already
  recorded in §3.4, screenshot every page, then set P1.6 to DONE.
- **Question I can now answer without AI:** why "coverage aligned with a service target" (Decision
  6) is only partly answerable today — the weeks-of-cover number exists, but the numeric service
  target it would need to be compared against (`ASM-08`) was registered as an assumption and never
  actually wired into any calculation or table.
