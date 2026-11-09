"""Planning KPI logic for the Alpiflow Control Tower (P1.5): the projected-
inventory recurrence, weeks of cover, and replenishment suggestions
(docs/BUSINESS_RULES.md §4). Capacity utilisation and supplier OTIF are
derived directly from existing `analytics` tables via SQL views
(`sql/006_planning_outputs.sql`) rather than Python here - they need no new
input data, only a ratio.
"""
