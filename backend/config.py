"""Runtime configuration for local Support Knowledge Miner services."""

from __future__ import annotations

from dataclasses import dataclass
import os
from urllib.parse import urlparse

_ALLOWED_LOCAL_DATABASE_HOSTS = {"localhost", "127.0.0.1", "::1", "postgres"}


@dataclass(frozen=True)
class DatabaseSettings:
    """Database connection settings constrained to local/dev targets."""

    url: str

    @classmethod
    def from_env(cls) -> "DatabaseSettings":
        url = os.environ.get("SKM_DATABASE_URL")
        if not url:
            url = (
                "postgresql://support_knowledge_miner:"
                "support_knowledge_miner_dev_password@localhost:5432/"
                "support_knowledge_miner"
            )
        return cls(url=_require_local_database_url(url))


def _require_local_database_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"postgresql", "postgres"}:
        raise ValueError("SKM_DATABASE_URL must use a PostgreSQL URL scheme")
    if parsed.hostname not in _ALLOWED_LOCAL_DATABASE_HOSTS:
        raise ValueError(
            "SKM_DATABASE_URL must target a confirmed local Docker/test database"
        )
    return url
