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
    assert "CREATE TABLE IF NOT EXISTS embeddings" in migration
    assert "embedding vector" in migration
    assert "dimensions integer NOT NULL" in migration
    assert "source_object_type IN ('message_pair')" in migration
