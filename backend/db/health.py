"""Backend database health checks."""

from __future__ import annotations

from dataclasses import dataclass

from backend.config import DatabaseSettings
from backend.db.connection import open_database_connection


@dataclass(frozen=True)
class DatabaseHealth:
    ok: bool
    database: str
    pgvector_available: bool
    pgvector_installed: bool


_HEALTH_QUERY = """
SELECT
    current_database() AS database,
    EXISTS(SELECT 1 FROM pg_available_extensions WHERE name = 'vector') AS pgvector_available,
    EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector') AS pgvector_installed
"""


def check_database_health(settings: DatabaseSettings | None = None) -> DatabaseHealth:
    """Return database and pgvector status for local smoke checks."""

    with open_database_connection(settings) as connection:
        row = connection.execute(_HEALTH_QUERY).fetchone()
    if row is None:
        raise RuntimeError("database health query returned no rows")
    return DatabaseHealth(
        ok=bool(row["pgvector_available"]) and bool(row["pgvector_installed"]),
        database=str(row["database"]),
        pgvector_available=bool(row["pgvector_available"]),
        pgvector_installed=bool(row["pgvector_installed"]),
    )
