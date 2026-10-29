-- P1.2 — analytics schema: star schema (dim_/fct_ prefixes), rebuildable from clean.
--
-- For this v1 slice, every table here has the same columns and constraints as its
-- clean counterpart (docs/ARCHITECTURE.md §3: "the first version of each table stays
-- deliberately simple — no layer is added just to look sophisticated"). The schema
-- boundary exists so analytics can later diverge (e.g. aggregation, slowly-changing
-- attributes) without touching clean, not because a difference exists today.
-- Column rationale: see sql/003_clean_tables.sql and docs/DATA_DICTIONARY.md.

CREATE TABLE IF NOT EXISTS analytics.dim_product (
    product_id      TEXT PRIMARY KEY,
    product_name    TEXT NOT NULL,
    family          TEXT NOT NULL
        CHECK (family IN ('FOOT', 'APPAREL', 'PACK', 'NUTRI')),
    size            TEXT,
    unit_of_measure TEXT NOT NULL DEFAULT 'piece',
    CONSTRAINT dim_product_size_matches_family
        CHECK (
            (family = 'FOOT' AND size IS NOT NULL)
            OR (family <> 'FOOT' AND size IS NULL)
        )
);

CREATE TABLE IF NOT EXISTS analytics.dim_calendar (
    calendar_date   DATE PRIMARY KEY,
    week_start_date DATE NOT NULL,
    iso_year        INTEGER NOT NULL,
    iso_week_number INTEGER NOT NULL
        CHECK (iso_week_number BETWEEN 1 AND 53)
);

CREATE TABLE IF NOT EXISTS analytics.dim_supplier (
    supplier_id   TEXT PRIMARY KEY,
    supplier_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analytics.fct_demand_actual (
    product_id      TEXT NOT NULL REFERENCES analytics.dim_product (product_id),
    week_start_date DATE NOT NULL REFERENCES analytics.dim_calendar (calendar_date),
    units_sold      INTEGER NOT NULL CHECK (units_sold >= 0),
    PRIMARY KEY (product_id, week_start_date)
);

CREATE TABLE IF NOT EXISTS analytics.fct_inventory_snapshot (
    product_id    TEXT NOT NULL REFERENCES analytics.dim_product (product_id),
    site_id       TEXT NOT NULL,
    snapshot_date DATE NOT NULL REFERENCES analytics.dim_calendar (calendar_date),
    on_hand_qty   INTEGER NOT NULL CHECK (on_hand_qty >= 0),
    allocated_qty INTEGER NOT NULL CHECK (allocated_qty >= 0),
    PRIMARY KEY (product_id, site_id, snapshot_date)
);

CREATE TABLE IF NOT EXISTS analytics.fct_purchase_order_line (
    order_id              TEXT NOT NULL,
    product_id            TEXT NOT NULL REFERENCES analytics.dim_product (product_id),
    supplier_id           TEXT NOT NULL REFERENCES analytics.dim_supplier (supplier_id),
    order_date            DATE NOT NULL,
    promised_receipt_date DATE NOT NULL,
    actual_receipt_date   DATE,
    ordered_qty           INTEGER NOT NULL CHECK (ordered_qty > 0),
    received_qty          INTEGER CHECK (received_qty IS NULL OR received_qty >= 0),
    status                TEXT NOT NULL
        CHECK (status IN (
            'draft', 'confirmed', 'partially_received', 'received',
            'cancelled_by_alpiflow', 'cancelled_by_supplier'
        )),
    PRIMARY KEY (order_id, product_id)
);

CREATE TABLE IF NOT EXISTS analytics.fct_capacity (
    site_id                  TEXT NOT NULL,
    family                   TEXT NOT NULL
        CHECK (family IN ('FOOT', 'APPAREL', 'PACK', 'NUTRI')),
    week_start_date          DATE NOT NULL REFERENCES analytics.dim_calendar (calendar_date),
    available_capacity_units INTEGER NOT NULL CHECK (available_capacity_units >= 0),
    planned_load_units       INTEGER NOT NULL CHECK (planned_load_units >= 0),
    PRIMARY KEY (site_id, family, week_start_date)
);
