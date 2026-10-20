"""Smoke test: verify the environment is usable.

It tests no business logic. Its only purpose is to answer the question "is my
environment correctly installed?" before starting Phase 1. It connects to no database.
"""

from __future__ import annotations

import pytest

from supply_planning import __version__
from supply_planning.config import (
    DEFAULT_POSTGRES_PORT,
    DatabaseSettings,
    load_database_settings,
    parse_port,
)


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


def test_port_defaults_to_5432_when_pgport_is_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """PGPORT is optional; load_database_settings falls back to 5432.

    Note what this test does NOT prove: the buggy
    `int(os.environ.get("PGPORT", "5432"))` also returns 5432 when the variable is
    absent, so this test stays green under both implementations. The regression is
    caught by the empty-value test below.
    """
    # The four required variables must be satisfied first, otherwise the function
    # raises KeyError before it ever reaches the port logic.
    monkeypatch.setenv("PGHOST", "localhost")
    monkeypatch.setenv("PGDATABASE", "supply_planning_lab")
    monkeypatch.setenv("PGUSER", "app")
    monkeypatch.setenv("PGPASSWORD", "s3cret")
    monkeypatch.delenv("PGPORT", raising=False)

    settings = load_database_settings(dotenv_path=str(tmp_path / "absent.env"))

    assert settings.port == DEFAULT_POSTGRES_PORT


def test_parse_port_uses_the_default_when_the_variable_is_absent() -> None:
    """An absent PGPORT means "no opinion", which is a legitimate default."""
    assert parse_port(None) == DEFAULT_POSTGRES_PORT


def test_parse_port_accepts_an_explicit_value() -> None:
    assert parse_port("5433") == 5433


@pytest.mark.parametrize("raw", ["", "   "])
def test_parse_port_rejects_an_empty_value(raw: str) -> None:
    """An empty PGPORT is a half-finished configuration, not an absent one.

    `os.environ.get("PGPORT", "5432")` would return "" here and never apply the
    default, then crash on int("") with an unreadable message.
    """
    with pytest.raises(ValueError, match="empty"):
        parse_port(raw)


@pytest.mark.parametrize("raw", ["abc", "54 33", "5432.0"])
def test_parse_port_rejects_a_non_integer_value(raw: str) -> None:
    with pytest.raises(ValueError, match="must be an integer"):
        parse_port(raw)


@pytest.mark.parametrize("raw", ["0", "-1", "70000"])
def test_parse_port_rejects_a_value_outside_the_valid_range(raw: str) -> None:
    with pytest.raises(ValueError, match="between 1 and 65535"):
        parse_port(raw)


def test_empty_pgport_is_rejected_by_load_database_settings(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """Wiring test: an empty PGPORT must reach parse_port and be rejected.

    This is the test that actually guards the fix. Reintroducing
    `int(os.environ.get("PGPORT", "5432"))` makes it fail with ValueError:
    invalid literal for int() with base 10: \'\' instead of the explicit message,
    whereas every parse_port unit test would stay green.
    """
    monkeypatch.setenv("PGHOST", "localhost")
    monkeypatch.setenv("PGDATABASE", "supply_planning_lab")
    monkeypatch.setenv("PGUSER", "app")
    monkeypatch.setenv("PGPASSWORD", "s3cret")
    monkeypatch.setenv("PGPORT", "")

    with pytest.raises(ValueError, match="PGPORT is set but empty"):
        load_database_settings(dotenv_path=str(tmp_path / "absent.env"))
