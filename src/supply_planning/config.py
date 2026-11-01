"""Configuration loading from the environment.

Project rule: no secret and no connection parameter is hard-coded. Everything comes
from environment variables, loaded from a local `.env` file that is never committed
(see `.env.example`).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

DEFAULT_POSTGRES_PORT = 5432


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

        A URL's host component cannot contain a `/` - but a Unix-socket `PGHOST`
        (e.g. Homebrew Postgres's `/tmp`) is a directory path, not a hostname.
        libpq/psycopg's own convention for that case is to leave the host empty
        and pass the socket directory as a `host` query parameter instead
        (bug found in P1.4: P1.2 only ever connected via the `psql` CLI, which
        takes `-h /tmp` directly and never went through this method).
        """
        secret = "***" if hide_password else self.password
        if self.host.startswith("/"):
            return (
                f"postgresql+psycopg://{self.user}:{secret}"
                f"@/{self.database}?host={self.host}&port={self.port}"
            )
        return (
            f"postgresql+psycopg://{self.user}:{secret}"
            f"@{self.host}:{self.port}/{self.database}"
        )


def parse_port(raw: str | None) -> int:
    """Turn the raw PGPORT value into a port number.

    Three cases are deliberately distinguished:

    - the variable is **absent** (`None`): the user has no opinion, so we apply
      `DEFAULT_POSTGRES_PORT`;
    - the variable is **present but empty**: the user started configuring and stopped,
      which is a broken state, so we raise instead of silently guessing;
    - the variable is **present and invalid**: we raise with the offending value.

    `os.environ.get()` collapses the first two cases by returning `""`, which is why
    the caller must pass the raw result of `os.environ.get("PGPORT")` without a default.
    """
    if raw is None:
        return DEFAULT_POSTGRES_PORT

    stripped = raw.strip()
    if not stripped:
        raise ValueError(
            "PGPORT is set but empty. Remove the line from .env to use the default "
            f"({DEFAULT_POSTGRES_PORT}), or give it an explicit value."
        )

    try:
        port = int(stripped)
    except ValueError as exc:
        raise ValueError(f"PGPORT must be an integer, got {raw!r}.") from exc

    if not 1 <= port <= 65535:
        raise ValueError(f"PGPORT must be between 1 and 65535, got {port}.")

    return port


def load_database_settings(*, dotenv_path: str | None = None) -> DatabaseSettings:
    """Read the PG* variables from the environment.

    Raises `KeyError` when a required variable is missing, instead of falling back to
    a silent default: a connection silently pointing at the wrong database is more
    dangerous than an explicit error.

    Raises `ValueError` when `PGPORT` is present but unusable. Two exception types are
    used on purpose: absence and invalidity are different problems for the caller, and
    the message must say which one occurred.
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
        port=parse_port(os.environ.get("PGPORT")),
        database=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
    )
