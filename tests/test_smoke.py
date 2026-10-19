"""Smoke test: verify the environment is usable.

It tests no business logic. Its only purpose is to answer the question "is my
environment correctly installed?" before starting Phase 1. It connects to no database.
"""

from __future__ import annotations

import pytest

from supply_planning import __version__
from supply_planning.config import DatabaseSettings, load_database_settings


def test_package_importable() -> None:
    assert __version__ == "0.1.0"


def test_core_dependencies_importable() -> None:
    """Every dependency listed in requirements.txt must import."""
    import pandas  # noqa: F401
    import psycopg  # noqa: F401
    import sqlalchemy  # noqa: F401


def test_sqlalchemy_url_is_built_correctly() -> None:
    settings = DatabaseSettings(
        host="localhost",
        port=5432,
        database="supply_planning_lab",
        user="app",
        password="s3cret",
    )
    assert settings.sqlalchemy_url() == (
        "postgresql+psycopg://app:s3cret@localhost:5432/supply_planning_lab"
    )


def test_sqlalchemy_url_can_hide_the_password() -> None:
    """The password must never appear in a URL intended for logs."""
    settings = DatabaseSettings(
        host="localhost",
        port=5432,
        database="supply_planning_lab",
        user="app",
        password="s3cret",
    )
    masked = settings.sqlalchemy_url(hide_password=True)
    assert "s3cret" not in masked
    assert "***" in masked


def test_missing_configuration_raises_instead_of_defaulting(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """Failure case: a missing variable must raise an explicit error.

    We point `load_dotenv` at a non-existent file so that the developer's local
    `.env` cannot influence the test result.
    """
    for name in ("PGHOST", "PGDATABASE", "PGUSER", "PGPASSWORD"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(KeyError) as excinfo:
        load_database_settings(dotenv_path=str(tmp_path / "absent.env"))

    assert "PGHOST" in str(excinfo.value)
