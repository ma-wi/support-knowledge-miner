"""Runtime configuration for local Support Knowledge Miner services."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from urllib.parse import quote, urlparse

_ALLOWED_LOCAL_DATABASE_HOSTS = {"localhost", "127.0.0.1", "::1", "postgres"}
_DEFAULT_POSTGRES_DB = "support_knowledge_miner"
_DEFAULT_POSTGRES_USER = "support_knowledge_miner"
_DEFAULT_POSTGRES_HOST = "localhost"
_DEFAULT_POSTGRES_PORT = "5432"
_REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
_LOCAL_DOCKER_ENV_FILES = (
    _REPOSITORY_ROOT / "deployment" / "docker" / ".env",
    _REPOSITORY_ROOT / "deployment" / "docker" / ".env.example",
)


@dataclass(frozen=True)
class DatabaseSettings:
    """Database connection settings constrained to local/dev targets."""

    url: str

    @classmethod
    def from_env(cls) -> "DatabaseSettings":
        url = os.environ.get("SKM_DATABASE_URL")
        if not url:
            url = _database_url_from_postgres_settings()
        return cls(url=_require_local_database_url(url))


def load_local_environment() -> None:
    """Load the local Docker env file without overriding explicit environment."""

    values = _local_docker_env_values()
    for key, value in values.items():
        os.environ.setdefault(key, value)


def _database_url_from_postgres_settings() -> str:
    values = _local_docker_env_values()
    database = os.environ.get("POSTGRES_DB") or values.get("POSTGRES_DB")
    username = os.environ.get("POSTGRES_USER") or values.get("POSTGRES_USER")
    password = os.environ.get("POSTGRES_PASSWORD") or values.get("POSTGRES_PASSWORD")
    host = os.environ.get("POSTGRES_HOST") or values.get("POSTGRES_HOST")
    port = os.environ.get("POSTGRES_PORT") or values.get("POSTGRES_PORT")
    selected_username = username or _DEFAULT_POSTGRES_USER
    return _build_postgres_url(
        database=database or _DEFAULT_POSTGRES_DB,
        username=selected_username,
        password=password or selected_username,
        host=host or _DEFAULT_POSTGRES_HOST,
        port=port or _DEFAULT_POSTGRES_PORT,
    )


def _local_docker_env_values() -> dict[str, str]:
    for path in _LOCAL_DOCKER_ENV_FILES:
        if path.is_file():
            return _read_env_file(path)
    return {}


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if not key:
            continue
        values[key] = _clean_env_file_value(value.strip())
    return values


def _clean_env_file_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _build_postgres_url(
    *, database: str, username: str, password: str, host: str, port: str
) -> str:
    return (
        f"postgresql://{quote(username, safe='')}:{quote(password, safe='')}"
        f"@{host}:{port}/{quote(database, safe='')}"
    )


def _require_local_database_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"postgresql", "postgres"}:
        raise ValueError("SKM_DATABASE_URL must use a PostgreSQL URL scheme")
    if parsed.hostname not in _ALLOWED_LOCAL_DATABASE_HOSTS:
        raise ValueError(
            "SKM_DATABASE_URL must target a confirmed local Docker/test database"
        )
    return url
