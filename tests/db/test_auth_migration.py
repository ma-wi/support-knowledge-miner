from __future__ import annotations

from importlib import resources

from backend.db.migrate import _migration_files


def test_auth_migration_is_ordered_after_foundation() -> None:
    names = [path.name for path in _migration_files()]

    assert names == [
        "0001_foundation.sql",
        "0002_auth_users_audit.sql",
        "0003_projects.sql",
        "0004_import_datasets.sql",
    ]


def test_auth_migration_defines_users_sessions_and_audit_without_plaintext_tokens() -> (
    None
):
    migration = (
        resources.files("backend.db.migrations")
        .joinpath("0002_auth_users_audit.sql")
        .read_text(encoding="utf-8")
    )

    assert "CREATE TABLE IF NOT EXISTS users" in migration
    assert "password_hash text NOT NULL" in migration
    assert "CREATE TABLE IF NOT EXISTS user_sessions" in migration
    assert "token_hash text NOT NULL UNIQUE" in migration
    assert "CREATE TABLE IF NOT EXISTS audit_events" in migration
    assert "actor_user_id uuid" in migration
    assert "access_token" not in migration
