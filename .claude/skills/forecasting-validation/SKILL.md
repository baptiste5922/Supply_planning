---
name: forecasting-validation
description: Use for exploratory time-series analysis, forecasting, model comparison, validation, forecast metrics or inventory scenarios.
---

# Forecasting and validation guide

## Problem definition

Specify target, forecast horizon, time grain, forecast creation date and intended decision before choosing a model.

## Exploration

- Check duplicates, missing dates, irregular intervals, outliers, stockout-censored sales and product lifecycle effects.
- Plot actual demand over time and by relevant segments.
- Distinguish zero sales from missing observations and unavailable-to-sell periods.
- Document promotions, seasonality and known data limitations.

## Validation

- Use chronological splits or rolling-origin backtesting.
- Never randomly shuffle time-series rows for final evaluation.
- Ensure features only use information available at forecast time.
- Compare against a simple baseline such as last period or seasonal naïve.
- Report MAE and RMSE; use MAPE only when zero/near-zero actuals and its interpretation are addressed.
- Evaluate metrics at the level where decisions are made (for example SKU-week and aggregate family).
- Inspect residuals and performance across seasons and product groups.
- Avoid claiming that a model improves decisions solely because one aggregate metric is lower.

## Inventory decisions

Forecasts are not replenishment policies. Replenishment also depends on lead time, stock position, capacity, order constraints and service goals. Keep these stages separate and test them independently.
