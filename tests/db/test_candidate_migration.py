from __future__ import annotations

from importlib import resources


def test_candidate_migration_defines_candidates_and_source_assignments() -> None:
    migration = (
        resources.files("backend.db.migrations")
        .joinpath("0008_candidates.sql")
        .read_text(encoding="utf-8")
    )

    assert "CREATE TABLE IF NOT EXISTS candidates" in migration
    assert "candidate_type IN" in migration
    assert "'static_faq'" in migration
    assert "auto_title text NOT NULL" in migration
    assert "manual_title text" in migration
    assert "manual_canonical_question text" in migration
    assert "CREATE TABLE IF NOT EXISTS candidate_source_assignments" in migration
    assert "candidate_id uuid NOT NULL REFERENCES candidates(id)" in migration
    assert "message_pair_id uuid NOT NULL REFERENCES message_pairs(id)" in migration
    assert "UNIQUE (project_id, source_cluster_id)" in migration
    assert "idx_candidate_sources_candidate" in migration
