from __future__ import annotations

from pathlib import Path
import os

import pytest

from backend import config
from backend.config import DatabaseSettings, _require_local_database_url


def test_database_url_accepts_local_postgres() -> None:
    url = "postgresql://user:pass@localhost:5432/support_knowledge_miner"
    assert _require_local_database_url(url) == url


def test_database_url_rejects_non_postgres_scheme() -> None:
    with pytest.raises(ValueError, match="PostgreSQL"):
        _require_local_database_url("mysql://user:pass@localhost/db")


def test_database_url_rejects_non_local_host() -> None:
    with pytest.raises(ValueError, match="local"):
        _require_local_database_url("postgresql://user:pass@example.com/db")


def test_database_settings_prefers_explicit_skm_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "SKM_DATABASE_URL",
        "postgresql://explicit:secret@localhost:5432/explicit_db",
    )
    monkeypatch.setenv("POSTGRES_DB", "ignored_db")

    assert (
        DatabaseSettings.from_env().url
        == "postgresql://explicit:secret@localhost:5432/explicit_db"
    )


def test_database_settings_derives_url_from_postgres_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SKM_DATABASE_URL", raising=False)
    monkeypatch.setattr(config, "_LOCAL_DOCKER_ENV_FILES", ())
    monkeypatch.setenv("POSTGRES_DB", "support_db")
    monkeypatch.setenv("POSTGRES_USER", "support_user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "local password")
    monkeypatch.setenv("POSTGRES_PORT", "55432")

    assert (
        DatabaseSettings.from_env().url
        == "postgresql://support_user:local%20password@localhost:55432/support_db"
    )


def test_database_settings_reads_local_docker_env_file_when_process_env_is_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "POSTGRES_DB=from_file_db",
                "POSTGRES_USER=from_file_user",
                "POSTGRES_PASSWORD='from file password'",
                "POSTGRES_PORT=55433",
            ]
        ),
        encoding="utf-8",
    )
    for key in (
        "SKM_DATABASE_URL",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_HOST",
        "POSTGRES_PORT",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(config, "_LOCAL_DOCKER_ENV_FILES", (env_file,))

    assert (
        DatabaseSettings.from_env().url
        == "postgresql://from_file_user:from%20file%20password@localhost:55433/from_file_db"
    )


def test_database_settings_rejects_non_local_postgres_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SKM_DATABASE_URL", raising=False)
    monkeypatch.setattr(config, "_LOCAL_DOCKER_ENV_FILES", ())
    monkeypatch.setenv("POSTGRES_HOST", "db.example.com")

    with pytest.raises(ValueError, match="local"):
        DatabaseSettings.from_env()


def test_load_local_environment_sets_missing_values_without_overriding_existing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "SKM_INITIAL_EMAIL=from-file@example.test",
                "SKM_INITIAL_PASSWORD=from-file-password",
                "POSTGRES_USER=from-file-user",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("SKM_INITIAL_EMAIL", raising=False)
    monkeypatch.delenv("POSTGRES_USER", raising=False)
    monkeypatch.setenv("SKM_INITIAL_PASSWORD", "explicit-password")
    monkeypatch.setattr(config, "_LOCAL_DOCKER_ENV_FILES", (env_file,))

    config.load_local_environment()

    assert os.environ["SKM_INITIAL_EMAIL"] == "from-file@example.test"
    assert os.environ["SKM_INITIAL_PASSWORD"] == "explicit-password"
    assert os.environ["POSTGRES_USER"] == "from-file-user"
