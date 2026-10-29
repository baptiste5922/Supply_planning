-- P1.2 — clean schema: typed, keyed, deduplicated. Plain table names (no dim_/fct_
-- prefix — that convention is reserved for analytics, docs/ARCHITECTURE.md §3).
-- Column-by-column rationale lives in docs/DATA_DICTIONARY.md; this file only encodes
-- what that document already decided.

-- 1. dim_product (docs/DATA_DICTIONARY.md §1)
CREATE TABLE IF NOT EXISTS clean.product (
    product_id      TEXT PRIMARY KEY,
    product_name    TEXT NOT NULL,
    family          TEXT NOT NULL
        CHECK (family IN ('FOOT', 'APPAREL', 'PACK', 'NUTRI')),
    size            TEXT,
    -- size is populated for FOOT only (size-level SKUs) and NULL everywhere else —
    -- both directions are enforced so a bug cannot silently merge the two states.
    unit_of_measure TEXT NOT NULL DEFAULT 'piece',
    -- No CHECK on unit_of_measure: the dictionary stores it (rather than hard-coding
    -- "piece" in code) precisely so a future unit change is a data change, not a
    -- migration. A CHECK here would defeat that.
    CONSTRAINT product_size_matches_family
        CHECK (
            (family = 'FOOT' AND size IS NOT NULL)
            OR (family <> 'FOOT' AND size IS NULL)
        )
);

-- 2. dim_calendar (docs/DATA_DICTIONARY.md §2)
CREATE TABLE IF NOT EXISTS clean.calendar (
    calendar_date   DATE PRIMARY KEY,
    week_start_date DATE NOT NULL,
    iso_year        INTEGER NOT NULL,
    iso_week_number INTEGER NOT NULL
        CHECK (iso_week_number BETWEEN 1 AND 53)
);
-- Note: a weekly fact's week_start_date can reference calendar(calendar_date)
-- directly, because the Monday of every week is itself a row in this table
-- (one row per date, not per week) — no separate "weeks" table is needed.

-- 3. dim_supplier (docs/DATA_DICTIONARY.md §3)
CREATE TABLE IF NOT EXISTS clean.supplier (
    supplier_id   TEXT PRIMARY KEY,
    supplier_name TEXT NOT NULL
    -- Deliberately no lead_time / MOQ columns here: docs/ARCHITECTURE.md §4 keeps
    -- those in configuration, keyed by product family, so there is one source of
    -- truth, not two.
);

-- 4. fct_demand_actual / sales (docs/DATA_DICTIONARY.md §4)
CREATE TABLE IF NOT EXISTS clean.demand_actual (
    product_id      TEXT NOT NULL REFERENCES clean.product (product_id),
    week_start_date DATE NOT NULL REFERENCES clean.calendar (calendar_date),
    units_sold      INTEGER NOT NULL CHECK (units_sold >= 0),
    -- Gross units, all channels combined, returns not deducted — both v1 decisions,
    -- see docs/BUSINESS_RULES.md §6. Grain completeness (every active SKU has a row
    -- every week, even units_sold = 0) is an ingestion-time rule (P1.4), not
    -- something a CHECK constraint can express here.
    PRIMARY KEY (product_id, week_start_date)
);

-- 5. fct_inventory_snapshot (docs/DATA_DICTIONARY.md §5)
CREATE TABLE IF NOT EXISTS clean.inventory_snapshot (
    product_id    TEXT NOT NULL REFERENCES clean.product (product_id),
    site_id       TEXT NOT NULL,
    -- Constant 'WH-01' in v1, no CHECK: the column exists so a multi-site extension
    -- is a data change, not a migration (same reasoning as unit_of_measure above).
    snapshot_date DATE NOT NULL REFERENCES clean.calendar (calendar_date),
    on_hand_qty   INTEGER NOT NULL CHECK (on_hand_qty >= 0),
    allocated_qty INTEGER NOT NULL CHECK (allocated_qty >= 0),
    -- available_qty = on_hand_qty - allocated_qty is intentionally NOT a stored
    -- column (docs/DATA_DICTIONARY.md §5) — storing it would create a second source
    -- of truth for one number. A negative result is a data-quality question for P1.4
    -- to raise, not something this table can refuse on insert without also refusing
    -- otherwise-valid rows that simply haven't been checked yet.
    PRIMARY KEY (product_id, site_id, snapshot_date)
);

-- 6. fct_purchase_order_line (docs/DATA_DICTIONARY.md §6)
CREATE TABLE IF NOT EXISTS clean.purchase_order_line (
    order_id              TEXT NOT NULL,
    product_id            TEXT NOT NULL REFERENCES clean.product (product_id),
    supplier_id           TEXT NOT NULL REFERENCES clean.supplier (supplier_id),
    order_date            DATE NOT NULL,
    promised_receipt_date DATE NOT NULL,
    -- Immutable once set, by process convention (docs/BUSINESS_RULES.md §4.4) — a
    -- CHECK constraint cannot enforce "never updated after the fact"; that rule
    -- belongs to the ingestion/application layer (P1.4/P1.5), not to the schema.
    actual_receipt_date   DATE,
    ordered_qty           INTEGER NOT NULL CHECK (ordered_qty > 0),
    received_qty          INTEGER CHECK (received_qty IS NULL OR received_qty >= 0),
    -- NULL = outcome unknown (line still open); 0 = confirmed zero received. The two
    -- must stay distinguishable (docs/DATA_DICTIONARY.md §6) — do not default to 0.
    status                TEXT NOT NULL
        CHECK (status IN (
            'draft', 'confirmed', 'partially_received', 'received',
            'cancelled_by_alpiflow', 'cancelled_by_supplier'
        )),
    -- The two cancellation reasons are kept distinct because the OTIF KPI
    -- (docs/BUSINESS_RULES.md §4.4) excludes one from the denominator and counts the
    -- other as a failure. Collapsing them would silently break that KPI.
    PRIMARY KEY (order_id, product_id)
    -- v1 simplification, stated in docs/DATA_DICTIONARY.md §6: at most one line per
    -- product per order. A split delivery is one line with status =
    -- 'partially_received', not a second line.
);

-- 7. fct_capacity (docs/DATA_DICTIONARY.md §7)
CREATE TABLE IF NOT EXISTS clean.capacity (
    site_id                  TEXT NOT NULL,
    family                   TEXT NOT NULL
        CHECK (family IN ('FOOT', 'APPAREL', 'PACK', 'NUTRI')),
    week_start_date          DATE NOT NULL REFERENCES clean.calendar (calendar_date),
    available_capacity_units INTEGER NOT NULL CHECK (available_capacity_units >= 0),
    planned_load_units       INTEGER NOT NULL CHECK (planned_load_units >= 0),
    PRIMARY KEY (site_id, family, week_start_date)
);
