---
name: supply-planning
description: Use when defining supply planning processes, inventory KPIs, demand-supply alignment, replenishment rules or S&OP scenarios.
---

# Supply planning analysis guide

## Start with the decision

For every metric or model, answer:
- Who uses it?
- What decision does it support?
- At what grain (SKU, product family, site, week)?
- What is its unit and time horizon?
- Which source fields are required?
- What action follows an exception?

## Define inventory states explicitly

Keep these concepts separate:
- On-hand inventory: physically recorded stock.
- Allocated/reserved inventory: stock committed to demand.
- Available inventory: the chosen definition of stock available for new demand.
- Inbound supply: expected receipts with dates and statuses.
- Projected inventory: expected balance over time after demand and supply events.

Document the chosen formula. Do not assume that on-hand inventory alone represents available stock.

## KPI definitions to consider

- Forecast error: actual demand compared with forecast at a defined grain.
- Inventory coverage: inventory divided by average demand over a stated period; state which inventory measure and demand window are used.
- Stockout risk: projected available inventory falls below zero or below a documented buffer.
- Capacity utilisation: planned load divided by available capacity, with compatible units.
- On-time delivery: define the denominator, requested date and actual/confirmed date.
- Service level: define whether this means line fill, unit fill, order fill or another measure.

## Planning logic

- Respect lead times, minimum order quantities, pack sizes and capacity only when represented in the data.
- Separate hard constraints from soft preferences.
- Make assumptions and thresholds configurable.
- Explain how missing lead times, zero demand and new products are handled.
- Test boundary cases and at least one scenario where no feasible plan exists.
- Label simulated rules clearly; do not present them as an industrial APS optimiser.
