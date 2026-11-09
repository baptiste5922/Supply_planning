-- P1.5 — planning outputs: the projected-inventory recurrence result, plus two
-- views deriving capacity utilisation and supplier OTIF directly from tables
-- that already exist. No new input data is needed for either view - this is
-- exactly the "clean answers trustworthy, analytics answers shaped for a
-- question" principle (docs/ARCHITECTURE.md §3) applied to planning outputs.
--
-- Naming note: docs/ARCHITECTURE.md §3 and docs/DATA_DICTIONARY.md §0 floated
-- `fct_planning_exception` as a placeholder name before this table's shape was
-- decided. `fct_projected_inventory` holds every week, not only the exception
-- ones - an "exception" (a shortage, an overload) is a WHERE filter on this
-- table or on fct_capacity, not a second table duplicating the same numbers.

-- 1. fct_projected_inventory (docs/BUSINESS_RULES.md §4, the "core calculation")
--    Grain: one row per (planning_origin_date, product_id, week_start_date).
--    `planning_origin_date` is part of the key, not a metadata column, so two
--    runs on two different Mondays coexist instead of overwriting each other -
--    "what did the plan say last week" is a real question this must answer.
CREATE TABLE IF NOT EXISTS analytics.fct_projected_inventory (
    planning_origin_date DATE NOT NULL REFERENCES analytics.dim_calendar (calendar_date),
    product_id           TEXT NOT NULL REFERENCES analytics.dim_product (product_id),
    week_start_date       DATE NOT NULL REFERENCES analytics.dim_calendar (calendar_date),
    weeks_ahead            INTEGER NOT NULL CHECK (weeks_ahead BETWEEN 0 AND 13),
    -- 0 = the planning origin itself (before that week's demand/receipts are
    -- applied); 1..13 = the recurrence's forward weeks.
    demand_units            INTEGER NOT NULL CHECK (demand_units >= 0),
    confirmed_receipt_units  INTEGER NOT NULL CHECK (confirmed_receipt_units >= 0),
    projected_inventory_units INTEGER NOT NULL,
    -- Deliberately NOT constrained to >= 0: a negative value is the shortage
    -- signal itself (docs/BUSINESS_RULES.md §4.2) and must never be clamped.
    safety_stock_units        INTEGER NOT NULL CHECK (safety_stock_units >= 0),
    projected_shortage_units   INTEGER NOT NULL CHECK (projected_shortage_units >= 0),
    -- = max(0, safety_stock_units - projected_inventory_units); an "exception"
    -- is simply a row here with projected_shortage_units > 0.
    weeks_of_cover              INTEGER,
    no_forward_demand            BOOLEAN,
    -- Both NULL for every row except weeks_ahead = 0 - weeks_of_cover is a
    -- property of the planning origin, not of each week, the same "legitimate
    -- NULL depending on context" pattern as dim_product.size.
    computed_at                   TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (planning_origin_date, product_id, week_start_date),
    CONSTRAINT weeks_of_cover_only_at_origin
        CHECK (
            (weeks_ahead = 0)
            OR (weeks_of_cover IS NULL AND no_forward_demand IS NULL)
        )
);

-- 2. Capacity utilisation (docs/BUSINESS_RULES.md §4.3) - pure ratio over an
--    existing table, deliberately NOT capped at 100% in the view itself (the
--    overload is exactly the information to surface, per the business rule).
CREATE OR REPLACE VIEW analytics.v_capacity_utilisation AS
SELECT
    site_id,
    family,
    week_start_date,
    available_capacity_units,
    planned_load_units,
    ROUND(100.0 * planned_load_units / available_capacity_units, 1) AS capacity_utilisation_pct
FROM analytics.fct_capacity
WHERE available_capacity_units > 0;
-- A row with available_capacity_units = 0 is excluded, not divided-by-zero:
-- that is itself a data-quality question for the ingestion report (P1.4), not
-- a utilisation percentage this view can compute.

-- 3. Supplier OTIF (docs/BUSINESS_RULES.md §4.4) - one row per supplier, over
--    every line whose promised_receipt_date falls in the past (a line not yet
--    due cannot be judged on time or late).
CREATE OR REPLACE VIEW analytics.v_supplier_otif AS
SELECT
    supplier_id,
    COUNT(*) AS lines_due,
    SUM(
        CASE
            WHEN status = 'received'
                 AND actual_receipt_date = promised_receipt_date
            THEN 1 ELSE 0
        END
    ) AS otif_lines,
    ROUND(
        100.0 * SUM(
            CASE
                WHEN status = 'received'
                     AND actual_receipt_date = promised_receipt_date
                THEN 1 ELSE 0
            END
        ) / COUNT(*),
        1
    ) AS supplier_otif_pct
FROM analytics.fct_purchase_order_line
WHERE status <> 'cancelled_by_alpiflow'
  -- excluded from the denominator entirely (docs/BUSINESS_RULES.md §4.4);
  -- every other status (including cancelled_by_supplier, partially_received,
  -- a draft/confirmed line already past its promised date) counts as due and,
  -- by the CASE above, as a failure unless received exactly on time.
  AND promised_receipt_date <= CURRENT_DATE
  -- "due in the period" (docs/BUSINESS_RULES.md §4.4): a line not yet due
  -- cannot be judged on-time or late, so it must not inflate either side of
  -- the ratio. This view is "OTIF to date"; a date-bounded period is a
  -- parameterised query, not something a plain view can express.
GROUP BY supplier_id;
