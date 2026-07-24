#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/../compose.yml"
PROJECT_NAME="${SKM_SMOKE_PROJECT_NAME:-skm-t003-smoke}"
POSTGRES_PORT="${SKM_SMOKE_POSTGRES_PORT:-55434}"
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

SKM_DATABASE_URL="${DATABASE_URL}" \
SKM_INITIAL_PASSWORD="owner-password" \
SKM_INITIAL_EMAIL="owner@example.test" \
SKM_INITIAL_FIRST_NAME="Local" \
SKM_INITIAL_LAST_NAME="Owner" \
uv run --locked python - <<'PY'
from time import sleep

from psycopg import OperationalError
from fastapi.testclient import TestClient

from backend.api import create_app
from backend.db import run_migrations
from backend.db.connection import open_database_connection

for attempt in range(30):
    try:
        run_migrations()
        break
    except OperationalError:
        if attempt == 29:
            raise
        sleep(1)

with TestClient(create_app()) as client:
    token_response = client.post(
        "/api/auth/sign-in",
        json={"email": "owner@example.test", "password": "owner-password"},
    )
    if token_response.status_code != 200:
        raise SystemExit(f"sign-in failed: {token_response.status_code}")
    token = token_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    alpha = client.post("/api/projects", headers=headers, json={"name": "Alpha"})
    beta = client.post("/api/projects", headers=headers, json={"name": "Beta"})
    if alpha.status_code != 201 or beta.status_code != 201:
        raise SystemExit("project creation failed")
    alpha_id = alpha.json()["id"]
    beta_id = beta.json()["id"]

    listed = client.get("/api/projects", headers=headers)
    names = {item["name"] for item in listed.json()}
    if names != {"Alpha", "Beta"}:
        raise SystemExit(f"unexpected project list: {names}")

    opened_beta = client.get(f"/api/projects/{beta_id}", headers=headers)
    if opened_beta.status_code != 200 or opened_beta.json()["name"] != "Beta":
        raise SystemExit("open project returned wrong project")

    renamed = client.patch(
        f"/api/projects/{alpha_id}",
        headers=headers,
        json={"name": "Alpha renamed"},
    )
    if renamed.status_code != 200 or renamed.json()["name"] != "Alpha renamed":
        raise SystemExit("project rename failed")

    bad_delete = client.request(
        "DELETE",
        f"/api/projects/{alpha_id}",
        headers=headers,
        json={"confirmation_name": "Alpha"},
    )
    if bad_delete.status_code != 400:
        raise SystemExit("project delete did not enforce name confirmation")

    deleted = client.request(
        "DELETE",
        f"/api/projects/{alpha_id}",
        headers=headers,
        json={"confirmation_name": "Alpha renamed"},
    )
    if deleted.status_code != 204:
        raise SystemExit("project delete failed")

    missing = client.get(f"/api/projects/{alpha_id}", headers=headers)
    remaining = client.get("/api/projects", headers=headers)
    if missing.status_code != 404:
        raise SystemExit("deleted project still opens")
    if [item["name"] for item in remaining.json()] != ["Beta"]:
        raise SystemExit("deleted project still listed or wrong project leaked")

with open_database_connection() as connection:
    audit_count = connection.execute(
        "SELECT COUNT(*) AS count FROM audit_events WHERE action LIKE 'project.%'"
    ).fetchone()
if audit_count is None or int(audit_count["count"]) < 4:
    raise SystemExit("project audit events were not persisted")
print("project_lifecycle_smoke=ok")
PY
