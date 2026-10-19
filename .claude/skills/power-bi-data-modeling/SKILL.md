---
name: power-bi-data-modeling
description: Use when designing the analytical schema, semantic model, DAX measures, dashboard pages or Power BI validation.
---

# Power BI and analytical modelling guide

## Model before visuals

- Define the grain of each fact table.
- Prefer a star schema where it fits: fact tables for events/measurements and dimensions for product, date, supplier, site and other descriptive entities.
- Use stable keys and explicit relationships.
- Avoid joining tables at different grains without understanding the multiplication risk.
- Define a proper date table for time-based reporting.

## Measures

For each measure, document:
- Business definition.
- Formula and unit.
- Expected aggregation behaviour.
- Filter context that should affect it.
- How to validate it against a small SQL result.

Prefer measures for context-dependent calculations; use calculated columns only when row-level stored logic is appropriate. Do not invent DAX syntax—verify it in Power BI.

## Dashboard design

- Start from user decisions, not chart variety.
- Give each page a clear question and audience.
- Use a small number of meaningful KPIs, trends, exceptions and drill-downs.
- Display units, time period and data freshness.
- Avoid misleading dual axes and unexplained red/green status.
- State if the data is synthetic.

## Validation

For every important KPI, compare Power BI output with a SQL query or hand-calculated fixture. Test slicers and cross-filtering. Document any limitations of the available Power BI environment.
