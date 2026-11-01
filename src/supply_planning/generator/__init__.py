"""Deterministic synthetic-data generator for the Alpiflow Control Tower (P1.3).

Every function here produces rows shaped for the `raw` schema
(`sql/002_raw_tables.sql`): the same columns, plus ingestion metadata
(`source_system`, `source_file`, `extracted_at`, `load_id`). See
`docs/DATA_DICTIONARY.md` for the business meaning of each field and
`docs/BUSINESS_RULES.md` §5 for the ASM-xx assumptions this module encodes.

All data produced here is synthetic and must never be mistaken for a real extract.
"""
