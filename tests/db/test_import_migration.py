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
        "0005_providers_profiles.sql",
        "0006_analysis_runs.sql",
        "0007_clusters.sql",
        "0008_candidates.sql",
        "0009_exports.sql",
        "0010_ollama_provider.sql",
        "0011_email_identity.sql",
        "0012_import_snake_case_fields.sql",
        "0013_remove_prompt_identifier_run_mode.sql",
        "0014_indexing_runs_without_profiles.sql",
        "0015_cluster_sets_llm_summaries.sql",
        "0016_explorer_exports.sql",
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


def test_import_snake_case_migration_renames_both_source_id_columns() -> None:
    migration = (
        resources.files("backend.db.migrations")
        .joinpath("0012_import_snake_case_fields.sql")
        .read_text(encoding="utf-8")
    )

    assert "RENAME COLUMN ticketid TO ticket_id" in migration
    assert "RENAME COLUMN messagegroupid TO message_group_id" in migration
