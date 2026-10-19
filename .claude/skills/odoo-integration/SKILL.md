---
name: odoo-integration
description: Use when planning or implementing an Odoo ERP connection, API integration, ERP entities or ERP-to-analytics workflows.
---

# Odoo integration guide

## Safe integration principles

- Use a dedicated test instance and synthetic records.
- Confirm the Odoo version and supported API before choosing an integration method.
- Prefer documented external APIs or supported export mechanisms.
- Never write directly to Odoo's internal PostgreSQL tables.
- Store API credentials in environment variables; never commit them.
- Request only the fields needed and handle pagination, access rights, timeouts and partial failure.
- Make imports traceable and safe to rerun where practical.

## Keep responsibilities separate

- Odoo is the operational source for ERP entities and transactions.
- The analytics database stores extracted and transformed data for reporting and analysis.
- Document the source of truth for each field.
- Record extraction time and any transformations.
- Do not imply that the educational APS simulator is connected to a commercial APS unless it really is.

## Before implementing

Document:
- Odoo version and API method.
- Entities and fields required.
- Authentication method and permissions.
- Expected volumes and pagination.
- Error and retry behaviour.
- Test strategy and rollback approach.
