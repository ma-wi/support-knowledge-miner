from __future__ import annotations

from importlib import resources


def test_provider_profile_migration_defines_global_settings_and_profiles() -> None:
    migration = (
        resources.files("backend.db.migrations")
        .joinpath("0005_providers_profiles.sql")
        .read_text(encoding="utf-8")
    )

    assert "CREATE TABLE IF NOT EXISTS provider_configurations" in migration
    assert "api_key_secret text" in migration
    assert "CONSTRAINT provider_configurations_provider_check" in migration
    assert "CREATE TABLE IF NOT EXISTS analysis_profiles" in migration
    assert (
        "project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE"
        in migration
    )
    assert "CONSTRAINT analysis_profiles_project_name_unique" in migration
    assert "api_key_plaintext" not in migration
