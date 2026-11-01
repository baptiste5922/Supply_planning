-- P1.3 — add the stockout-censoring flag, closing the open question in
-- docs/BUSINESS_RULES.md §6 ("Stockout-censored sales"). Decided when the generator
-- was built, not before (docs/DATA_DICTIONARY.md §4): a demand-actual row where
-- units_sold = 0 can mean "no demand" or "the SKU was out of stock and we only
-- recorded the unmet part as zero" — the two are different facts, and collapsing
-- them would hide the second case from the Phase 2 forecasting EDA (P2.1).
--
-- A follow-up file, not an edit to sql/002_raw_tables.sql, by the decision recorded
-- in docs/SESSION_LOG.md (P1.2): raw table shapes are a forecast of what the P1.3
-- generator actually produces, and a shape change is a migration, not a rewrite.

-- raw: loose-typed, like every other raw column (docs/ARCHITECTURE.md §3).
ALTER TABLE raw.demand_actual
    ADD COLUMN IF NOT EXISTS was_stocked_out TEXT;

-- clean/analytics: typed boolean, NOT NULL. DEFAULT FALSE only lets the ALTER
-- succeed against any pre-existing rows; it is dropped immediately afterwards so
-- that every future insert must state the flag explicitly — a silent default here
-- would re-introduce exactly the "0 means unknown" ambiguity this column exists to
-- remove.
ALTER TABLE clean.demand_actual
    ADD COLUMN IF NOT EXISTS was_stocked_out BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE clean.demand_actual
    ALTER COLUMN was_stocked_out DROP DEFAULT;

ALTER TABLE analytics.fct_demand_actual
    ADD COLUMN IF NOT EXISTS was_stocked_out BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE analytics.fct_demand_actual
    ALTER COLUMN was_stocked_out DROP DEFAULT;
