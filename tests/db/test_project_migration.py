from __future__ import annotations

from importlib import resources


def test_project_migration_defines_lifecycle_and_audit_actor_columns() -> None:
    migration = (
        resources.files("backend.db.migrations")
        .joinpath("0003_projects.sql")
        .read_text(encoding="utf-8")
    )

    assert "CREATE TABLE IF NOT EXISTS projects" in migration
    assert "lifecycle_state text NOT NULL DEFAULT 'active'" in migration
    assert "created_by_user_id uuid REFERENCES users(id)" in migration
    assert "updated_by_user_id uuid REFERENCES users(id)" in migration
    assert "deleted_at timestamptz" in migration
