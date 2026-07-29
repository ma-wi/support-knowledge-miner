"""PostgreSQL connection factory."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from pgvector.psycopg import register_vector
from psycopg import Connection, connect
from psycopg.rows import dict_row

from backend.config import DatabaseSettings


@contextmanager
def open_database_connection(
    settings: DatabaseSettings | None = None,
    *,
    register_pgvector_types: bool = True,
) -> Iterator[Connection[dict[str, object]]]:
    """Open a PostgreSQL connection using local-safe settings."""

    resolved = settings or DatabaseSettings.from_env()
    with connect(resolved.url, row_factory=dict_row) as connection:
        if register_pgvector_types:
            register_vector(connection)
            connection.commit()
        yield connection
