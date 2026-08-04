from __future__ import annotations

from importlib import resources


def test_provider_migration_defines_global_settings_before_profile_removal() -> None:
    migration = (
        resources.files("backend.db.migrations")
        .joinpath("0005_providers_profiles.sql")
        .read_text(encoding="utf-8")
    )

    assert "CREATE TABLE IF NOT EXISTS provider_configurations" in migration
    assert "api_key_secret text" in migration
    assert "CONSTRAINT provider_configurations_provider_check" in migration
    assert "provider IN ('openai', 'ollama', 'vllm')" in migration
    assert "CREATE TABLE IF NOT EXISTS analysis_profiles" in migration
    assert (
        "project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE"
        in migration
    )
    assert "CONSTRAINT analysis_profiles_project_name_unique" in migration
    assert "api_key_plaintext" not in migration


def test_profile_tables_are_removed_by_indexing_forward_migration() -> None:
    migration = (
        resources.files("backend.db.migrations")
        .joinpath("0014_indexing_runs_without_profiles.sql")
        .read_text(encoding="utf-8")
    )

    assert "DROP TABLE IF EXISTS analysis_profiles" in migration
    assert "DROP COLUMN IF EXISTS analysis_profile_id" in migration


def test_ollama_provider_migration_extends_existing_constraints() -> None:
    migration = (
        resources.files("backend.db.migrations")
        .joinpath("0010_ollama_provider.sql")
        .read_text(encoding="utf-8")
    )

    assert (
        "DROP CONSTRAINT IF EXISTS provider_configurations_provider_check" in migration
    )
    assert "DROP CONSTRAINT IF EXISTS analysis_profiles_provider_check" in migration
    assert "DROP CONSTRAINT IF EXISTS analysis_runs_provider_check" in migration
    assert "provider IN ('openai', 'ollama', 'vllm')" in migration
