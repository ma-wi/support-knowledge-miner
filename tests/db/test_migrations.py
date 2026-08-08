from __future__ import annotations

from importlib import resources

from backend.db.migrate import _migration_files


def test_migration_files_are_ordered() -> None:
    names = [path.name for path in _migration_files()]
    assert names == sorted(names)
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


def test_foundation_migration_enables_pgvector() -> None:
    migration = resources.files("backend.db.migrations").joinpath("0001_foundation.sql")
    assert "CREATE EXTENSION IF NOT EXISTS vector" in migration.read_text(
        encoding="utf-8"
    )


def test_removed_prompt_and_run_mode_fields_have_forward_migration() -> None:
    migration = resources.files("backend.db.migrations").joinpath(
        "0013_remove_prompt_identifier_run_mode.sql"
    )
    sql = migration.read_text(encoding="utf-8")

    assert "DROP COLUMN prompt_identifier" in sql
    assert "profile_snapshot - 'prompt_identifier'" in sql
    assert "parameters - 'mode'" in sql


def test_analysis_profiles_have_destructive_forward_migration() -> None:
    migration = resources.files("backend.db.migrations").joinpath(
        "0014_indexing_runs_without_profiles.sql"
    )
    sql = migration.read_text(encoding="utf-8")

    assert "TRUNCATE TABLE" in sql
    assert "DROP TABLE IF EXISTS analysis_profiles" in sql
    assert "DROP COLUMN IF EXISTS analysis_profile_id" in sql
    assert "DROP COLUMN IF EXISTS profile_snapshot" in sql
    assert "ADD COLUMN IF NOT EXISTS phase text" in sql
    assert "ADD COLUMN IF NOT EXISTS error_code text" in sql
    assert "ADD COLUMN IF NOT EXISTS display_name text" in sql
    assert "UPDATE export_logs" in sql


def test_explorer_export_migration_replaces_candidate_export_types() -> None:
    migration = resources.files("backend.db.migrations").joinpath(
        "0016_explorer_exports.sql"
    )
    sql = migration.read_text(encoding="utf-8")

    assert "ADD COLUMN IF NOT EXISTS cluster_set_id uuid" in sql
    assert "DROP TABLE IF EXISTS candidate_source_assignments" in sql
    assert "DROP TABLE IF EXISTS candidates" in sql
    assert "export_type IN ('explorer_csv', 'explorer_json')" in sql
    assert "candidate_csv" in sql
    assert "source_assignment_csv" in sql


def test_provider_instance_migration_removes_active_vllm_and_adds_provenance() -> None:
    migration = resources.files("backend.db.migrations").joinpath(
        "0017_provider_instances_and_global_jobs.sql"
    )
    sql = migration.read_text(encoding="utf-8")

    assert "ADD COLUMN IF NOT EXISTS id uuid" in sql
    assert "ADD COLUMN IF NOT EXISTS display_name text" in sql
    assert "DELETE FROM provider_configurations" in sql
    assert "WHERE provider = 'vllm'" in sql
    assert "ADD CONSTRAINT provider_configurations_pkey PRIMARY KEY (id)" in sql
    assert "provider IN ('openai', 'ollama')" in sql
    assert "provider IN ('openai', 'ollama', 'vllm')" not in sql
    assert (
        "provider_configuration_id uuid REFERENCES provider_configurations(id)" in sql
    )
    assert (
        "llm_provider_configuration_id uuid REFERENCES provider_configurations(id)"
        in sql
    )
    assert "provider_display_name text" in sql
    assert "llm_provider_display_name text" in sql
    assert "idx_analysis_runs_global_active" in sql
    assert "idx_cluster_sets_global_active" in sql
    assert "status IN ('queued', 'running', 'cancelling')" in sql


def test_provider_available_models_migration_splits_discovery_from_allow_lists() -> (
    None
):
    migration = resources.files("backend.db.migrations").joinpath(
        "0018_provider_available_models.sql"
    )
    sql = migration.read_text(encoding="utf-8")

    assert "ADD COLUMN IF NOT EXISTS available_models jsonb" in sql
    assert "provider_configurations_available_models_array_check" in sql
    assert "DROP COLUMN IF EXISTS supports_embedding" in sql
    assert "DROP COLUMN IF EXISTS supports_llm" in sql
    assert "COALESCE(pc.embedding_models, '[]'::jsonb)" in sql
    assert "COALESCE(pc.llm_models, '[]'::jsonb)" in sql
