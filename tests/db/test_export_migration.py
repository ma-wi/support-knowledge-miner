from __future__ import annotations

from importlib import resources


def test_export_migration_defines_export_history_metadata() -> None:
    migration = (
        resources.files("backend.db.migrations")
        .joinpath("0009_exports.sql")
        .read_text(encoding="utf-8")
    )

    assert "CREATE TABLE IF NOT EXISTS export_logs" in migration
    assert "export_type text NOT NULL" in migration
    assert "include_original_text boolean NOT NULL DEFAULT false" in migration
    assert "dataset_version_id uuid REFERENCES dataset_versions(id)" in migration
    assert "analysis_run_id uuid REFERENCES analysis_runs(id)" in migration
    assert "output_filename text NOT NULL" in migration
    assert "row_count integer NOT NULL DEFAULT 0" in migration
    assert "idx_export_logs_project_created" in migration
