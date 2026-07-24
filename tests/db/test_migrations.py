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
    ]


def test_foundation_migration_enables_pgvector() -> None:
    migration = resources.files("backend.db.migrations").joinpath("0001_foundation.sql")
    assert "CREATE EXTENSION IF NOT EXISTS vector" in migration.read_text(
        encoding="utf-8"
    )
