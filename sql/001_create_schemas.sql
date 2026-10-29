-- P1.2 — three-schema layering (docs/ARCHITECTURE.md §3).
-- raw: source-shaped, loose types, append-only landing zone, never rebuilt.
-- clean: typed, keyed, deduplicated — "is this row trustworthy".
-- analytics: star schema (dim_/fct_), rebuildable from clean — "is this row shaped for a question".

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS clean;
CREATE SCHEMA IF NOT EXISTS analytics;
