from __future__ import annotations

from importlib import resources

from backend.db.migrate import _migration_files


def test_import_migration_is_ordered_after_projects() -> None:
    names = [path.name for path in _migration_files()]

    assert names == [
        "0001_foundation.sql",
        "0002_auth_users_audit.sql",
        "0003_projects.sql",
        "0004_import_datasets.sql",
    ]


def test_import_migration_defines_project_scoped_dataset_and_log_tables() -> None:
    migration = (
        resources.files("backend.db.migrations")
        .joinpath("0004_import_datasets.sql")
        .read_text(encoding="utf-8")
    )

    assert "CREATE TABLE IF NOT EXISTS import_logs" in migration
    assert (
        "project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE"
        in migration
    )
    assert "CREATE TABLE IF NOT EXISTS dataset_versions" in migration
    assert "CONSTRAINT dataset_versions_project_version_unique" in migration
    assert "CREATE TABLE IF NOT EXISTS message_pairs" in migration
    assert "CREATE TABLE IF NOT EXISTS import_log_entries" in migration
