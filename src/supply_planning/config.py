"""Configuration loading from the environment.

Project rule: no secret and no connection parameter is hard-coded. Everything comes
from environment variables, loaded from a local `.env` file that is never committed
(see `.env.example`).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class DatabaseSettings:
    """Connection settings for the analytical PostgreSQL database."""

    host: str
    port: int
    database: str
    user: str
    password: str

    def sqlalchemy_url(self, *, hide_password: bool = False) -> str:
        """Build the SQLAlchemy URL.

        Use `hide_password=True` for logs and error messages: a password must never
        be written to a console output or a log file.
        """
        secret = "***" if hide_password else self.password
        return (
            f"postgresql+psycopg://{self.user}:{secret}"
            f"@{self.host}:{self.port}/{self.database}"
        )


def load_database_settings(*, dotenv_path: str | None = None) -> DatabaseSettings:
    """Read the PG* variables from the environment.

    Raises `KeyError` when a required variable is missing, instead of falling back to
    a silent default: a connection silently pointing at the wrong database is more
    dangerous than an explicit error.
    """
    load_dotenv(dotenv_path=dotenv_path, override=False)

    required = ("PGHOST", "PGDATABASE", "PGUSER", "PGPASSWORD")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise KeyError(
            "Missing environment variables: "
            + ", ".join(missing)
            + ". Copy .env.example to .env and fill in your local values."
        )

    return DatabaseSettings(
        host=os.environ["PGHOST"],
        port=int(os.environ.get("PGPORT", "5432")),
        database=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
    )
