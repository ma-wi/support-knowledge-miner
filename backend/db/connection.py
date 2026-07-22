"""PostgreSQL connection factory."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from psycopg import Connection, connect
from psycopg.rows import dict_row

from backend.config import DatabaseSettings


@contextmanager
def open_database_connection(
    settings: DatabaseSettings | None = None,
) -> Iterator[Connection[dict[str, object]]]:
    """Open a PostgreSQL connection using local-safe settings."""

    resolved = settings or DatabaseSettings.from_env()
    with connect(resolved.url, row_factory=dict_row) as connection:
        yield connection
