from __future__ import annotations

import pytest

from backend.config import _require_local_database_url


def test_database_url_accepts_local_postgres() -> None:
    url = "postgresql://user:pass@localhost:5432/support_knowledge_miner"
    assert _require_local_database_url(url) == url


def test_database_url_rejects_non_postgres_scheme() -> None:
    with pytest.raises(ValueError, match="PostgreSQL"):
        _require_local_database_url("mysql://user:pass@localhost/db")


def test_database_url_rejects_non_local_host() -> None:
    with pytest.raises(ValueError, match="local"):
        _require_local_database_url("postgresql://user:pass@example.com/db")
