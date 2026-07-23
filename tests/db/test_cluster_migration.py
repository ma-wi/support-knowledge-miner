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
