"""Deterministic SQL migration runner for the local PostgreSQL database."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources

from backend.config import DatabaseSettings
from backend.db.connection import open_database_connection

_MIGRATION_PACKAGE = "backend.db.migrations"
_SCHEMA_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version text PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT now()
)
"""


@dataclass(frozen=True)
class MigrationResult:
    applied_versions: tuple[str, ...]


def _migration_files() -> list[resources.abc.Traversable]:
    migration_root = resources.files(_MIGRATION_PACKAGE)
    return sorted(
        (
            path
            for path in migration_root.iterdir()
            if path.is_file() and path.name.endswith(".sql")
        ),
        key=lambda path: path.name,
    )


def run_migrations(settings: DatabaseSettings | None = None) -> MigrationResult:
    """Apply unapplied SQL migrations in filename order."""

    applied: list[str] = []
    with open_database_connection(
        settings,
        register_pgvector_types=False,
    ) as connection:
        with connection.transaction():
            connection.execute(_SCHEMA_TABLE_SQL)
            existing_rows = connection.execute(
                "SELECT version FROM schema_migrations"
            ).fetchall()
            existing = {str(row["version"]) for row in existing_rows}
            for path in _migration_files():
                version = path.name
                if version in existing:
                    continue
                connection.execute(path.read_text(encoding="utf-8"))
                connection.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s)",
                    (version,),
                )
                applied.append(version)
    return MigrationResult(applied_versions=tuple(applied))
