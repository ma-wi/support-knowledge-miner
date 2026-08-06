from __future__ import annotations

from pathlib import Path


COMPOSE_FILE = Path("deployment/docker/compose.yml")
ENV_EXAMPLE_FILE = Path("deployment/docker/.env.example")
SMOKE_SCRIPT = Path("deployment/docker/scripts/smoke-postgres.sh")
MIGRATION_SMOKE_SCRIPT = Path("deployment/docker/scripts/smoke-migrations.sh")


def test_compose_defines_pgvector_postgres_with_persistent_volume() -> None:
    compose = COMPOSE_FILE.read_text(encoding="utf-8")
    assert "pgvector/pgvector:pg17" in compose
    assert "postgres-data:/var/lib/postgresql/data" in compose
    assert "postgres-data:" in compose
    assert "pg_isready" in compose


def test_compose_has_no_active_vllm_runtime_path() -> None:
    compose = COMPOSE_FILE.read_text(encoding="utf-8")
    env_example = ENV_EXAMPLE_FILE.read_text(encoding="utf-8")

    assert "vllm" not in compose.lower()
    assert "skm_vllm" not in env_example.lower()


def test_compose_defines_ollama_path_with_persistent_model_store() -> None:
    compose = COMPOSE_FILE.read_text(encoding="utf-8")
    env_example = ENV_EXAMPLE_FILE.read_text(encoding="utf-8")
    assert "ollama:" in compose
    assert 'profiles: ["ollama"]' in compose
    assert "ollama/ollama:latest" in compose
    assert "11434" in compose
    assert "ollama-data:/root/.ollama" in compose
    assert "ollama-data:" in compose
    assert "OLLAMA_KEEP_ALIVE: ${OLLAMA_KEEP_ALIVE:-5m}" in compose
    assert "OLLAMA_KEEP_ALIVE=5m" in env_example


def test_postgres_smoke_script_verifies_migration_health_and_restart_persistence() -> (
    None
):
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")
    assert "run_migrations()" in script
    assert "check_database_health()" in script
    assert "restart postgres" in script
    assert "smoke_persistence_marker" in script
    assert "down -v" in script


def test_migration_smoke_script_executes_fresh_and_existing_database_paths() -> None:
    script = MIGRATION_SMOKE_SCRIPT.read_text(encoding="utf-8")
    assert "0010_ollama_provider.sql" in script
    assert "0018_provider_available_models.sql" in script
    assert "0011_email_identity.sql" in script
    assert "id, provider, display_name, manual_models, available_models" in script
    assert "legacy username column remains" in script
    assert "accepted an unsupported provider" in script
    assert "AuthService(upgrade).sign_in" in script
    assert "down -v" in script
