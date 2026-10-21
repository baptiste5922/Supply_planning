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
