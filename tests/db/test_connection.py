from __future__ import annotations

from typing import Any

import backend.db.connection as connection_module
from backend.config import DatabaseSettings
from backend.db.connection import open_database_connection


class FakeConnection:
    def __init__(self) -> None:
        self.commits = 0

    def __enter__(self) -> FakeConnection:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def commit(self) -> None:
        self.commits += 1


def test_connection_factory_registers_pgvector_types(
    monkeypatch: Any,
) -> None:
    connection = FakeConnection()
    registered: list[FakeConnection] = []
    monkeypatch.setattr(
        connection_module,
        "connect",
        lambda *_args, **_kwargs: connection,
    )
    monkeypatch.setattr(
        connection_module,
        "register_vector",
        registered.append,
    )

    with open_database_connection(
        DatabaseSettings("postgresql://local.test"),
    ) as opened:
        assert opened is connection

    assert registered == [connection]
    assert connection.commits == 1


def test_migration_connection_can_skip_pgvector_registration(
    monkeypatch: Any,
) -> None:
    connection = FakeConnection()
    monkeypatch.setattr(
        connection_module,
        "connect",
        lambda *_args, **_kwargs: connection,
    )
    monkeypatch.setattr(
        connection_module,
        "register_vector",
        lambda *_args: raise_unexpected_registration(),
    )

    with open_database_connection(
        DatabaseSettings("postgresql://local.test"),
        register_pgvector_types=False,
    ) as opened:
        assert opened is connection

    assert connection.commits == 0


def raise_unexpected_registration() -> None:
    raise AssertionError("pgvector registration must be skipped")
