-- P1.2 — raw schema: one table per source, loose types, append-only.
--
-- Design rules (docs/ARCHITECTURE.md §3):
--   * Business columns are TEXT. raw holds exactly what the source said, even if it
--     is malformed — typing and validation are clean's job (P1.4), not raw's.
--   * No constraint on business columns, and no uniqueness on business keys: raw is
--     append-only, so the same source row can legitimately land twice across two
--     loads. Deduplication happens when moving raw -> clean.
--   * Every row carries ingestion metadata so a later question ("was this wrong at
--     the source, or did my code break it?") is always answerable.
--   * `raw_id` is a technical surrogate key for the raw row itself, not a business key.

CREATE TABLE IF NOT EXISTS raw.product (
    raw_id        BIGSERIAL PRIMARY KEY,
    product_id    TEXT,
    product_name  TEXT,
    family        TEXT,
    size          TEXT,
    unit_of_measure TEXT,
    source_system TEXT NOT NULL,
    source_file   TEXT,
    extracted_at  TIMESTAMPTZ NOT NULL,
    load_id       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.calendar (
    raw_id          BIGSERIAL PRIMARY KEY,
    calendar_date   TEXT,
    week_start_date TEXT,
    iso_year        TEXT,
    iso_week_number TEXT,
    source_system   TEXT NOT NULL,
    source_file     TEXT,
    extracted_at    TIMESTAMPTZ NOT NULL,
    load_id         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.supplier (
    raw_id        BIGSERIAL PRIMARY KEY,
    supplier_id   TEXT,
    supplier_name TEXT,
    source_system TEXT NOT NULL,
    source_file   TEXT,
    extracted_at  TIMESTAMPTZ NOT NULL,
    load_id       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.demand_actual (
    raw_id          BIGSERIAL PRIMARY KEY,
    product_id      TEXT,
    week_start_date TEXT,
    units_sold      TEXT,
    source_system   TEXT NOT NULL,
    source_file     TEXT,
    extracted_at    TIMESTAMPTZ NOT NULL,
    load_id         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.inventory_snapshot (
    raw_id        BIGSERIAL PRIMARY KEY,
    product_id    TEXT,
    site_id       TEXT,
    snapshot_date TEXT,
    on_hand_qty   TEXT,
    allocated_qty TEXT,
    source_system TEXT NOT NULL,
    source_file   TEXT,
    extracted_at  TIMESTAMPTZ NOT NULL,
    load_id       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.purchase_order_line (
    raw_id                 BIGSERIAL PRIMARY KEY,
    order_id               TEXT,
    product_id             TEXT,
    supplier_id            TEXT,
    order_date             TEXT,
    promised_receipt_date  TEXT,
    actual_receipt_date    TEXT,
    ordered_qty            TEXT,
    received_qty           TEXT,
    status                 TEXT,
    source_system          TEXT NOT NULL,
    source_file            TEXT,
    extracted_at           TIMESTAMPTZ NOT NULL,
    load_id                TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.capacity (
    raw_id                   BIGSERIAL PRIMARY KEY,
    site_id                  TEXT,
    family                   TEXT,
    week_start_date          TEXT,
    available_capacity_units TEXT,
    planned_load_units       TEXT,
    source_system            TEXT NOT NULL,
    source_file              TEXT,
    extracted_at             TIMESTAMPTZ NOT NULL,
    load_id                  TEXT NOT NULL
);
