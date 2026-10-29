# Roadmap

Status values: `TODO`, `IN_PROGRESS`, `BLOCKED`, `DONE`. Do not mark a task DONE until its acceptance criteria are satisfied.

## Phase 0 — Setup and project understanding (6–10 hours)

### P0.1 — Define the fictional business and decisions
- Status: DONE (2026-10-19)
- Deliverable: `docs/BUSINESS_RULES.md`
- Acceptance criteria:
  - Company, product families, planning grain and users are described.
  - At least five business questions are listed.
  - All invented values are labelled as assumptions.

### P0.2 — Create repository and Python environment
- Status: DONE (2026-10-19)
- Deliverable: initial folders, dependency file, `.env.example`, `.gitignore`
- Acceptance criteria:
  - Clean environment can be created from README instructions.
  - Secrets and raw private data are excluded by `.gitignore`.
  - A minimal smoke test runs.

### P0.3 — Learn the data flow
- Status: DONE (2026-10-20)
- Deliverable: `docs/ARCHITECTURE.md`
- Acceptance criteria:
  - Diagram shows source → Python → PostgreSQL → Power BI.
  - Odoo is shown as an optional operational source for Phase 3.
  - Responsibilities and source-of-truth decisions are documented.

## Phase 1 — Supply Planning Control Tower (35–50 hours)

### P1.1 — Define data grain, dictionary and KPI rules
- Status: DONE (2026-10-21)
- Deliverables: `docs/DATA_DICTIONARY.md`, `docs/BUSINESS_RULES.md`
- Acceptance criteria:
  - Product, date/week, sales, inventory, purchase/supply and capacity fields are defined.
  - Units, grain, keys and missing-data rules are explicit.
  - Inventory and delivery KPIs have formulas and caveats.

### P1.2 — Design PostgreSQL schema
- Status: DONE (2026-10-29)
- Deliverables: versioned SQL under `sql/`
- Acceptance criteria:
  - Primary/foreign keys and relevant constraints are defined.
  - Table grain is documented.
  - Schema can be created on a fresh development database.
  - No Odoo internal tables are modified.

### P1.3 — Build a small synthetic dataset
- Status: TODO
- Deliverables: deterministic data generator and small sample fixture
- Acceptance criteria:
  - Re-running generation produces reproducible records.
  - Includes normal cases and documented edge cases.
  - Data is clearly labelled synthetic.

### P1.4 — Implement ingestion and quality checks
- Status: TODO
- Deliverables: reusable Python modules under `src/`
- Acceptance criteria:
  - Ingestion is logged and reports row counts.
  - Invalid records are reported rather than silently discarded.
  - Duplicate and missing-key checks exist.
  - At least one automated test covers a failure case.

### P1.5 — Calculate planning KPIs and exceptions
- Status: TODO
- Deliverables: SQL/Python logic and tests
- Acceptance criteria:
  - Demand, supply, capacity and projected inventory are distinguishable.
  - Coverage and shortage definitions are documented.
  - Results match hand-calculated examples.
  - Zero demand and missing lead-time behaviour are tested.

### P1.6 — Build Power BI report
- Status: TODO
- Deliverables: report file or documented report specification plus screenshots
- Acceptance criteria:
  - Product/time filtering works.
  - KPI definitions and units are visible.
  - Important measures reconcile to SQL.
  - Synthetic data is disclosed.

### P1.7 — Publish and explain milestone
- Status: TODO
- Acceptance criteria:
  - README includes setup, architecture, demo and limitations.
  - User can explain the data model, one SQL query and three KPIs.
  - Reviewer agent has no unresolved blockers.

## Phase 2 — Demand Forecasting & Inventory Optimisation (30–45 hours)

### P2.1 — Build weekly demand dataset and perform EDA
- Status: TODO
- Acceptance criteria:
  - Duplicates, missing periods, zero sales and outliers are investigated.
  - Product lifecycle and stockout-censored sales limitations are considered.
  - EDA notebook is reproducible; reusable functions live in `src/`.

### P2.2 — Define forecast experiment
- Status: TODO
- Acceptance criteria:
  - Target, grain, horizon and forecast origin are explicit.
  - Chronological validation is used.
  - Leakage risks are documented.

### P2.3 — Implement baseline and statistical model
- Status: TODO
- Acceptance criteria:
  - Seasonal naïve or other appropriate simple baseline is evaluated.
  - At least one suitable statistical model is compared.
  - MAE/RMSE are calculated at documented grains.
  - MAPE is used only with caveats if relevant.
  - Model performance is reported by relevant segments where feasible.

### P2.4 — Translate forecast into planning scenarios
- Status: TODO
- Acceptance criteria:
  - Forecasting and replenishment policy remain separate components.
  - Lead time, current stock and inbound supply are accounted for where data exists.
  - At least three scenarios are compared.
  - Assumptions are configurable.

### P2.5 — Integrate forecast outputs into reporting
- Status: TODO
- Acceptance criteria:
  - Actuals, forecasts and errors are distinguishable.
  - Dashboard metrics reconcile to saved evaluation results.
  - Limitations are visible.

### P2.6 — Publish and explain milestone
- Status: TODO
- Acceptance criteria:
  - README documents validation design and baseline comparison.
  - User can explain leakage, the split strategy and the chosen metrics.
  - Reviewer agent has no unresolved blockers.

## Phase 3 — ERP-to-APS Digital Transformation Simulator (35–55 hours)

### P3.1 — Learn Odoo data and API basics
- Status: TODO
- Acceptance criteria:
  - Odoo version and supported API method are documented.
  - Test instance uses synthetic data.
  - Read-only extraction works before any write operation is considered.

### P3.2 — Map business process
- Status: TODO
- Deliverables: current/future process diagram
- Acceptance criteria:
  - Roles, inputs, decisions, outputs and exceptions are represented.
  - Unclear business rules are listed as open questions.

### P3.3 — Write requirements and user stories
- Status: TODO
- Deliverables: `docs/requirements/`
- Acceptance criteria:
  - Requirements have stable IDs and priorities.
  - User stories include testable acceptance criteria.
  - Non-functional concerns such as data quality and auditability are considered.

### P3.4 — Build traceability matrix and test plan
- Status: TODO
- Acceptance criteria:
  - Each priority requirement links to design elements and test cases.
  - Positive, negative and boundary scenarios are covered.
  - Test data is reproducible.

### P3.5 — Integrate ERP extract with analytical model
- Status: TODO
- Acceptance criteria:
  - Supported API/export is used.
  - Credentials remain outside source control.
  - Pagination, errors and reruns are handled appropriately.
  - Source-of-truth fields are documented.
  - Odoo's internal tables are not directly modified.

### P3.6 — Simulate APS rules and monitor exceptions
- Status: TODO
- Acceptance criteria:
  - Simulation is clearly labelled and its limitations documented.
  - Business rules are configurable and tested.
  - Missing data and infeasible scenarios are visible to the user.

### P3.7 — Publish and explain milestone
- Status: TODO
- Acceptance criteria:
  - A demo follows one requirement from business need to test evidence.
  - User can explain one user story, its acceptance criteria and linked tests.
  - Reviewer agent has no unresolved blockers.

## Phase 4 — Portfolio integration and interview preparation (15–25 hours)

### P4.1 — Consistent end-to-end demo
- Status: TODO
- Acceptance criteria:
  - Shared product/time keys and naming are consistent.
  - Data flow across projects is documented.
  - Demo can be reproduced from a clean setup.

### P4.2 — Final portfolio review
- Status: TODO
- Acceptance criteria:
  - README, screenshots, limitations and data provenance are complete.
  - No secrets or private data are committed.
  - Tests and setup instructions are accurate.

### P4.3 — Interview practice
- Status: TODO
- Acceptance criteria:
  - Prepare a 3-minute project explanation.
  - Answer questions about supply KPIs, SQL joins, forecast validation, ERP integration and user stories.
  - Perform one small code/query change without AI assistance.

## Working rule

Only one major task should be `IN_PROGRESS` at a time. Keep tasks small enough to finish in one or a few focused sessions. If a task exceeds its estimate by 50%, stop and reduce scope before adding complexity.
