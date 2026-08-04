from __future__ import annotations

from importlib import resources


def test_cluster_migration_defines_clusters_memberships_and_traceability() -> None:
    migration = (
        resources.files("backend.db.migrations")
        .joinpath("0007_clusters.sql")
        .read_text(encoding="utf-8")
    )

    assert "CREATE TABLE IF NOT EXISTS clusters" in migration
    assert "manual_title text" in migration
    assert (
        "auto_status IN ('unreviewed', 'in_progress', 'reviewed', 'rejected', 'outlier')"
        in migration
    )
    assert "CREATE TABLE IF NOT EXISTS cluster_memberships" in migration
    assert "message_pair_id uuid NOT NULL REFERENCES message_pairs(id)" in migration
    assert "UNIQUE (analysis_run_id, message_pair_id)" in migration
    assert "idx_clusters_project_run" in migration


def test_cluster_set_migration_adds_saved_sets_lineage_and_summary_state() -> None:
    migration = (
        resources.files("backend.db.migrations")
        .joinpath("0015_cluster_sets_llm_summaries.sql")
        .read_text(encoding="utf-8")
    )

    assert "CREATE TABLE IF NOT EXISTS cluster_sets" in migration
    assert "parent_cluster_set_id uuid REFERENCES cluster_sets(id)" in migration
    assert "vector_basis IN ('message', 'answer', 'combined')" in migration
    assert "llm_provider IS NULL OR llm_provider IN ('openai', 'ollama')" in migration
    assert "CREATE TABLE IF NOT EXISTS cluster_set_events" in migration
    assert "ADD COLUMN IF NOT EXISTS embedding_models jsonb" in migration
    assert "ADD COLUMN IF NOT EXISTS llm_models jsonb" in migration
    assert "provider_configurations_llm_models_array_check" in migration
    assert (
        "ADD COLUMN IF NOT EXISTS cluster_set_id uuid REFERENCES cluster_sets(id)"
        in migration
    )
    assert "ADD COLUMN IF NOT EXISTS auto_summary_question text" in migration
    assert "DROP CONSTRAINT IF EXISTS cluster_memberships_pair_unique" in migration
    assert "UNIQUE (cluster_set_id, message_pair_id)" in migration
    assert "idx_cluster_memberships_set" in migration
