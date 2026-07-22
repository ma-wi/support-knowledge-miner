#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/../compose.yml"
PROJECT_NAME="${SKM_SMOKE_PROJECT_NAME:-skm-t001-smoke}"
POSTGRES_PORT="${SKM_SMOKE_POSTGRES_PORT:-55432}"
DB_NAME="support_knowledge_miner"
DB_USER="support_knowledge_miner"
DB_PASSWORD="support_knowledge_miner_dev_password"
DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@localhost:${POSTGRES_PORT}/${DB_NAME}"

cleanup() {
  POSTGRES_PORT="${POSTGRES_PORT}" docker compose \
    -p "${PROJECT_NAME}" \
    -f "${COMPOSE_FILE}" \
    down -v >/dev/null 2>&1 || true
}
trap cleanup EXIT

POSTGRES_PORT="${POSTGRES_PORT}" docker compose \
  -p "${PROJECT_NAME}" \
  -f "${COMPOSE_FILE}" \
  up -d postgres

for _ in $(seq 1 30); do
  if POSTGRES_PORT="${POSTGRES_PORT}" docker compose \
    -p "${PROJECT_NAME}" \
    -f "${COMPOSE_FILE}" \
    exec -T postgres pg_isready -U "${DB_USER}" -d "${DB_NAME}" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

POSTGRES_PORT="${POSTGRES_PORT}" docker compose \
  -p "${PROJECT_NAME}" \
  -f "${COMPOSE_FILE}" \
  exec -T postgres pg_isready -U "${DB_USER}" -d "${DB_NAME}" >/dev/null

SKM_DATABASE_URL="${DATABASE_URL}" uv run --locked python - <<'PY'
from backend.db import check_database_health, run_migrations
from backend.db.connection import open_database_connection

result = run_migrations()
health = check_database_health()
if not health.ok:
    raise SystemExit("database health check failed after migration")
with open_database_connection() as connection:
    connection.execute(
        """
        INSERT INTO app_metadata (key, value)
        VALUES ('smoke_persistence_marker', 'before_restart')
        ON CONFLICT (key) DO UPDATE
        SET value = EXCLUDED.value,
            updated_at = now()
        """
    )
    connection.commit()
print(f"applied={result.applied_versions} pgvector_installed={health.pgvector_installed}")
PY

POSTGRES_PORT="${POSTGRES_PORT}" docker compose \
  -p "${PROJECT_NAME}" \
  -f "${COMPOSE_FILE}" \
  restart postgres >/dev/null

for _ in $(seq 1 30); do
  if POSTGRES_PORT="${POSTGRES_PORT}" docker compose \
    -p "${PROJECT_NAME}" \
    -f "${COMPOSE_FILE}" \
    exec -T postgres pg_isready -U "${DB_USER}" -d "${DB_NAME}" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

SKM_DATABASE_URL="${DATABASE_URL}" uv run --locked python - <<'PY'
from backend.db import check_database_health
from backend.db.connection import open_database_connection

health = check_database_health()
if not health.ok:
    raise SystemExit("database health check failed after restart")
with open_database_connection() as connection:
    row = connection.execute(
        "SELECT value FROM app_metadata WHERE key = 'smoke_persistence_marker'"
    ).fetchone()
if row is None or row["value"] != "before_restart":
    raise SystemExit("database state did not persist across restart")
print("restart_persistence=ok pgvector_installed=True")
PY
