# Supply Planning & Data Analytics Portfolio

A learning-first portfolio for demonstrating data analysis, supply planning, BI, forecasting, ERP integration and digital transformation skills.

## Projects

1. **Supply Planning Control Tower** — compare demand, supply, capacity and inventory.
2. **Demand Forecasting & Inventory Optimisation** — analyse weekly sales, evaluate forecasts and explore replenishment decisions.
3. **ERP-to-APS Digital Transformation Simulator** — model an Odoo-to-analytics workflow and document requirements, user stories, tests and traceability.

All examples must use public or synthetic data. This is an educational simulation, not an actual Salomon/Amer Sports implementation.

## Getting started

Tested on macOS with Python 3.14.3 and PostgreSQL installed via Homebrew.

```bash
# 1. Isolated virtual environment (never committed)
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 3. Local configuration (never commit .env)
cp .env.example .env
#    then edit .env with your local PostgreSQL values

# 4. Create a least-privilege role and a dev database, then the schema (P1.2)
#    Run as a PostgreSQL superuser once; PGUSER/PGDATABASE must match your .env.
createuser --login --pwprompt supply_planning_app
createdb --owner=supply_planning_app supply_planning_lab
for f in sql/*.sql; do psql -d supply_planning_lab -U supply_planning_app -f "$f"; done

# 5. Verification: the smoke test must pass
python -m pytest
```

Expected result at step 5: `17 passed`. The smoke test connects to no database; it
only checks that the package and its dependencies import, and that configuration
loading refuses to start with missing variables.

Step 4 creates `raw`, `clean` and `analytics` schemas with 7 tables each
(`docs/DATA_DICTIONARY.md`), with their keys and constraints — see
`docs/ARCHITECTURE.md` §3 for why the three schemas exist. If your machine already
runs a PostgreSQL server on the default port for other work, point `PGHOST`/`PGPORT`
in `.env` at a separate instance or port rather than reusing that one.

### Adding a dependency

Dependencies are pinned in `requirements.txt`. Only add one when a roadmap task
genuinely requires it, with a comment explaining what it is for.

## How to use this repository with Claude Code in VS Code

1. Open this repository as the workspace.
2. Read `CLAUDE.md` and `docs/PROJECT_BRIEF.md`.
3. Start with the first unchecked task in `docs/ROADMAP.md`.
4. Ask Claude to explain the task and propose a small plan before coding.
5. Work in small increments and run the relevant tests.
6. At the end of each session, update `docs/SESSION_LOG.md`.

Suggested first prompt:

> Read CLAUDE.md, docs/PROJECT_BRIEF.md and docs/ROADMAP.md. Do not write code yet. Explain the first roadmap task, the business context, the concepts I need to learn, its acceptance criteria, and how we will verify it. Ask me one short question only if a decision blocks progress.

## Suggested stack

- Python 3.12+ (choose a version compatible with installed dependencies)
- PostgreSQL
- pandas, SQLAlchemy and psycopg
- Power BI Desktop for reporting
- Odoo in a separate test instance for ERP exercises
- pytest for automated tests
- Jupyter for exploration, with reusable logic kept in `src/`

Do not install everything at once. Add tools when the relevant roadmap task needs them.

## Suggested initial structure

```text
.
├── CLAUDE.md
├── README.md
├── .env.example
├── .gitignore
├── .claude/
│   ├── README.md
│   ├── agents/
│   └── skills/
├── docs/
│   ├── PROJECT_BRIEF.md
│   ├── ROADMAP.md
│   ├── DATA_DICTIONARY.md
│   ├── ARCHITECTURE.md
│   └── SESSION_LOG.md
├── data/
│   ├── raw/
│   ├── processed/
│   └── sample/
├── notebooks/
├── sql/
├── src/
└── tests/
```

## Important

This bundle defines project context and a roadmap; it does not yet contain the full application implementation or Power BI report. Build those incrementally against the roadmap.
