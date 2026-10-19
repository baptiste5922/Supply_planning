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
