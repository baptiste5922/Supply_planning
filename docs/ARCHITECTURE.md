# Architecture (initial proposal)

## Logical flow

```text
Synthetic/public sources ─┐
                          ├─> Python ingestion and validation
Odoo test instance ───────┘             |
                                        v
                               PostgreSQL analytics DB
                               - raw/staging layer
                               - cleaned layer
                               - analytics model
                                  |           |
                                  v           v
                               Power BI    Forecasting
                                           experiments
```

## Component responsibilities

- **Sources:** public or synthetic sales, product, stock, supplier, capacity and purchase-order data. Odoo may become a source in Phase 3.
- **Python:** extraction, validation, transformation, logs, forecasting experiments and tests.
- **PostgreSQL:** persistent analytical storage, constraints, relationships and queryable data products.
- **Power BI:** interactive reporting and business-facing measures.
- **Odoo:** operational ERP demonstration; use supported APIs/exports, not direct writes to its internal tables.
- **Tests:** verify schema, transformations, planning calculations and forecast evaluation.

## Data layers

Use a simple medallion-style structure only where it adds clarity:
- **Raw/staging:** source-shaped records with extraction metadata.
- **Cleaned:** validated types, keys and consistent units.
- **Analytics:** facts/dimensions or other clearly documented tables designed for reporting.

Do not add a separate physical database/schema for every layer unless the project needs it. Keep the first version easy to understand.

## Initial design decisions to revisit

- Weekly grain for demand and planning is the initial proposal.
- Product/SKU is the principal planning entity.
- Data is synthetic until a suitable public dataset is selected.
- Forecasting starts with a baseline before more complex models.
- The APS component is a rules-based simulation, not an optimiser or commercial APS.
