#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/../compose.yml"
PROJECT_NAME="${SKM_SMOKE_PROJECT_NAME:-skm-t004-smoke}"
POSTGRES_PORT="${SKM_SMOKE_POSTGRES_PORT:-55435}"
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
        raise SystemExit("sign-in failed")
    headers = {"Authorization": f"Bearer {token_response.json()['access_token']}"}
    project = client.post("/api/projects", headers=headers, json={"name": "Imports"})
    if project.status_code != 201:
        raise SystemExit("project creation failed")
    project_id = project.json()["id"]

    csv_import = client.post(
        f"/api/projects/{project_id}/imports",
        headers=headers,
        json={
            "source_type": "csv",
            "source_name": "fixture.csv",
            "content": (
                "ticketid,messagegroupid,message,answer\n"
                "T-1,G-1,Hello,Answer\n"
                "T-1,G-1,Duplicate,Answer 2\n"
                "T-2,G-2, ,Missing message\n"
            ),
        },
    )
    if csv_import.status_code != 201:
        raise SystemExit(f"csv import failed: {csv_import.status_code}")
    csv_payload = csv_import.json()
    if csv_payload["log"]["valid_records"] != 2:
        raise SystemExit("csv valid count mismatch")
    if csv_payload["log"]["skipped_records"] != 1:
        raise SystemExit("csv skipped count mismatch")
    if csv_payload["dataset_version"] is None:
        raise SystemExit("csv import did not create dataset version")

    bad_headers = client.post(
        f"/api/projects/{project_id}/imports",
        headers=headers,
        json={
            "source_type": "csv",
            "source_name": "bad.csv",
            "content": "ticketid,message,answer\nT-1,Hi,A\n",
        },
    )
    if bad_headers.status_code != 201:
        raise SystemExit("missing-header import did not create log response")
    if bad_headers.json()["dataset_version"] is not None:
        raise SystemExit("missing-header import created dataset version")
    if bad_headers.json()["log"]["status"] != "failed":
        raise SystemExit("missing-header import was not failed")

    json_import = client.post(
        f"/api/projects/{project_id}/imports",
        headers=headers,
        json={
            "source_type": "json",
            "source_name": "fixture.json",
            "content": '[{"ticketid":"J-1","messagegroupid":"G-1","message":"Hi","answer":"A"}]',
        },
    )
    if json_import.status_code != 201 or json_import.json()["log"]["valid_records"] != 1:
        raise SystemExit("json import failed")

    logs = client.get(f"/api/projects/{project_id}/imports", headers=headers)
    if logs.status_code != 200 or len(logs.json()) != 3:
        raise SystemExit("import logs were not persisted")

with open_database_connection() as connection:
    pair_count = connection.execute("SELECT COUNT(*) AS count FROM message_pairs").fetchone()
    log_count = connection.execute("SELECT COUNT(*) AS count FROM import_logs").fetchone()
if int(pair_count["count"]) != 3:
    raise SystemExit("message pairs were not persisted as expected")
if int(log_count["count"]) != 3:
    raise SystemExit("import logs were not persisted as expected")
print("imports_smoke=ok")
PY
