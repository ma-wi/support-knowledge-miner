from __future__ import annotations

from importlib import resources


def test_analysis_run_migration_defines_runs_and_embedding_seam() -> None:
    migration = (
        resources.files("backend.db.migrations")
        .joinpath("0006_analysis_runs.sql")
        .read_text(encoding="utf-8")
    )

    assert "CREATE TABLE IF NOT EXISTS analysis_runs" in migration
    assert (
        "status IN ('queued', 'running', 'completed', 'failed', 'cancelled')"
        in migration
    )
    assert "profile_snapshot jsonb NOT NULL" in migration
    assert "dataset_version_id uuid NOT NULL REFERENCES dataset_versions" in migration
    assert "provider IN ('openai', 'ollama', 'vllm')" in migration
    assert "CREATE TABLE IF NOT EXISTS embeddings" in migration
    assert "embedding vector" in migration
    assert "dimensions integer NOT NULL" in migration
    assert "source_object_type IN ('message_pair')" in migration


def test_indexing_run_forward_migration_removes_profile_dependency() -> None:
    migration = (
        resources.files("backend.db.migrations")
        .joinpath("0014_indexing_runs_without_profiles.sql")
        .read_text(encoding="utf-8")
    )

    assert (
        "DROP CONSTRAINT IF EXISTS analysis_runs_analysis_profile_id_fkey" in migration
    )
    assert "DROP COLUMN IF EXISTS analysis_profile_id" in migration
    assert "DROP COLUMN IF EXISTS profile_snapshot" in migration
    assert "'cancelling'" in migration
    assert "embeddings" in migration
    assert "DROP COLUMN IF EXISTS analysis_profile_id" in migration
