"""PostgreSQL connection helper, shared by ingestion (P1.4) and later planning
logic (P1.5) - one place builds the SQLAlchemy engine from `DatabaseSettings`
(`config.py`), so a connection is never opened ad hoc with its own URL-building.
"""

from __future__ import annotations

from sqlalchemy import Engine, create_engine

from .config import DatabaseSettings


def make_engine(settings: DatabaseSettings) -> Engine:
    return create_engine(settings.sqlalchemy_url())
