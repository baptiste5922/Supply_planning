# Data Dictionary — Draft

This is a starting point, not a final schema. Confirm every field and grain before implementing tables.

| Entity | Candidate fields | Intended grain / notes |
|---|---|---|
| Product | product_id, SKU, product_name, family, season, unit_of_measure | One row per SKU |
| Calendar | date, week_start, month, season, year | One row per date or week, as documented |
| Demand actual | product_id, week_start, units_sold, sales_value, promotion_flag | One row per SKU-week; distinguish zero from missing |
| Demand forecast | product_id, forecast_origin, target_week, forecast_units, model_version | One row per SKU-origin-target week-model |
| Inventory snapshot | product_id, site_id, snapshot_date, on_hand, allocated, available | One row per SKU-site-snapshot |
| Purchase/supply order | order_id, product_id, supplier_id, order_date, expected_receipt_date, ordered_qty, received_qty, status | One row per order line |
| Supplier | supplier_id, supplier_name, lead_time_days, minimum_order_qty | One row per supplier; lead time assumptions must be documented |
| Capacity plan | site_id, week_start, product_family, available_capacity, planned_load, unit | One row per site-week-family |
| Planning exception | exception_id, product_id, week_start, exception_type, severity, explanation | One row per detected exception |

## Rules to decide before implementation

- Are quantities units, cases, pairs or another unit?
- Does available stock already subtract allocations?
- Are sales lost during stockouts or simply recorded as zero?
- Is capacity measured in units, hours or another unit?
- How are cancelled, delayed and partially received orders represented?
- Are timestamps local or UTC?
- What is the source of truth for each field?

Do not implement all candidate fields automatically. Select the smallest set needed for the first vertical slice.
