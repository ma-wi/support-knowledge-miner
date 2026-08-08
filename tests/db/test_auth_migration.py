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
        "0017_provider_instances_and_global_jobs.sql",
        "0018_provider_available_models.sql",
        "0019_project_ticket_url_template.sql",
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
    assert "username text NOT NULL UNIQUE" in migration
    assert "password_hash text NOT NULL" in migration
    assert "CREATE TABLE IF NOT EXISTS user_sessions" in migration
    assert "token_hash text NOT NULL UNIQUE" in migration
    assert "CREATE TABLE IF NOT EXISTS audit_events" in migration
    assert "actor_user_id uuid" in migration
    assert "access_token" not in migration


def test_email_identity_upgrade_removes_legacy_username_and_detects_collisions() -> (
    None
):
    migration = (
        resources.files("backend.db.migrations")
        .joinpath("0011_email_identity.sql")
        .read_text(encoding="utf-8")
    )

    assert "legacy_user.username = email_user.email" in migration
    assert "DROP COLUMN IF EXISTS username" in migration
    assert "CREATE INDEX IF NOT EXISTS idx_users_active_email" in migration
