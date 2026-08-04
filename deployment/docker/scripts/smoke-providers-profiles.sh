#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/../compose.yml"
PROJECT_NAME="${SKM_SMOKE_PROJECT_NAME:-skm-t005-smoke}"
POSTGRES_PORT="${SKM_SMOKE_POSTGRES_PORT:-55436}"
DB_NAME="support_knowledge_miner"
DB_USER="support_knowledge_miner"
DB_PASSWORD="support_knowledge_miner_dev_password"
DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@localhost:${POSTGRES_PORT}/${DB_NAME}"

run_compose() {
  POSTGRES_DB="${DB_NAME}" \
    POSTGRES_USER="${DB_USER}" \
    POSTGRES_PASSWORD="${DB_PASSWORD}" \
    POSTGRES_PORT="${POSTGRES_PORT}" \
    docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" "$@"
}

cleanup() {
  run_compose down -v >/dev/null 2>&1 || true
}
trap cleanup EXIT

run_compose up -d postgres

for _ in $(seq 1 30); do
  if run_compose exec -T postgres \
    pg_isready -U "${DB_USER}" -d "${DB_NAME}" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

run_compose exec -T postgres \
  pg_isready -U "${DB_USER}" -d "${DB_NAME}" >/dev/null

SKM_DATABASE_URL="${DATABASE_URL}" \
SKM_INITIAL_PASSWORD="owner-password" \
SKM_INITIAL_EMAIL="owner@example.test" \
SKM_INITIAL_FIRST_NAME="Local" \
SKM_INITIAL_LAST_NAME="Owner" \
uv run --locked python - <<'PY'
from time import sleep
import os

from psycopg import OperationalError
from fastapi.testclient import TestClient

from backend.api import create_app
from backend.db import run_migrations
from backend.db.connection import open_database_connection
from backend.providers.secrets import generate_provider_secret_key

for attempt in range(30):
    try:
        run_migrations()
        break
    except OperationalError:
        if attempt == 29:
            raise
        sleep(1)

secret = "sk-local-smoke-secret"
os.environ["SKM_PROVIDER_ENCRYPTION_KEY"] = generate_provider_secret_key()
with TestClient(create_app()) as client:
    token_response = client.post(
        "/api/auth/sign-in",
        json={"email": "owner@example.test", "password": "owner-password"},
    )
    if token_response.status_code != 200:
        raise SystemExit("sign-in failed")
    headers = {"Authorization": f"Bearer {token_response.json()['access_token']}"}

    openai = client.put(
        "/api/providers/openai",
        headers=headers,
        json={
            "api_key": secret,
            "manual_models": ["text-embedding-3-small", "gpt-4.1-mini"],
        },
    )
    if openai.status_code != 200 or not openai.json()["api_key_set"]:
        raise SystemExit("openai provider configuration failed")
    if secret in str(openai.json()):
        raise SystemExit("openai secret leaked in write response")

    vllm = client.put(
        "/api/providers/vllm",
        headers=headers,
        json={
            "endpoint_url": "http://localhost:8000",
            "manual_models": ["local-embed", "local-chat"],
        },
    )
    if vllm.status_code != 200:
        raise SystemExit("vllm provider configuration failed")

    listed = client.get("/api/providers", headers=headers)
    if listed.status_code != 200 or secret in str(listed.json()):
        raise SystemExit("provider listing failed or leaked secret")

    with open_database_connection() as connection:
        stored_secret = connection.execute(
            "SELECT api_key_secret FROM provider_configurations WHERE provider = 'openai'"
        ).fetchone()["api_key_secret"]
    if stored_secret == secret or not str(stored_secret).startswith("fernet:"):
        raise SystemExit("openai credential was not encrypted in storage")

    project = client.post("/api/projects", headers=headers, json={"name": "Indexing"})
    if project.status_code != 201:
        raise SystemExit("project creation failed")
    project_id = project.json()["id"]

    imported = client.post(
        f"/api/projects/{project_id}/imports",
        headers={
            **headers,
            "Content-Type": "text/csv",
            "Content-Disposition": "attachment; filename*=UTF-8''smoke.csv",
        },
        content=(
            b"ticket_id,message_group_id,message,answer\n"
            b"T-1,G-1,How do I reset it?,Use the reset link.\n"
        ),
    )
    if imported.status_code != 201:
        raise SystemExit(f"import failed: {imported.text}")
    dataset_id = imported.json()["dataset_version"]["id"]

    local_run = client.post(
        f"/api/projects/{project_id}/indexing-runs",
        headers=headers,
        json={
            "dataset_version_id": dataset_id,
            "provider": "vllm",
            "model": "local-embed",
        },
    )
    if local_run.status_code != 201:
        raise SystemExit(f"local indexing run creation failed: {local_run.text}")
    if local_run.json()["provider"] != "vllm":
        raise SystemExit("local indexing run provider was not persisted")

    rejected_cloud = client.post(
        f"/api/projects/{project_id}/indexing-runs",
        headers=headers,
        json={
            "dataset_version_id": dataset_id,
            "provider": "openai",
            "model": "gpt-4.1-mini",
        },
    )
    if (
        rejected_cloud.status_code != 400
        or rejected_cloud.json().get("code")
        != "INDEXING_CLOUD_CONFIRMATION_REQUIRED"
    ):
        raise SystemExit("openai indexing run was not gated by confirmation")

    cloud_run = client.post(
        f"/api/projects/{project_id}/indexing-runs",
        headers=headers,
        json={
            "dataset_version_id": dataset_id,
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "cloud_use_confirmed": True,
        },
    )
    if cloud_run.status_code != 201:
        raise SystemExit(f"cloud indexing run creation failed: {cloud_run.text}")
    if cloud_run.json()["provider"] != "openai":
        raise SystemExit("cloud indexing run provider was not persisted")

    runs = client.get(f"/api/projects/{project_id}/indexing-runs", headers=headers)
    if runs.status_code != 200 or len(runs.json()) != 2:
        raise SystemExit("indexing runs were not persisted")
    if any("analysis_profile_id" in run for run in runs.json()):
        raise SystemExit("indexing run response exposed an analysis profile id")

    removed = client.put(
        "/api/providers/openai",
        headers=headers,
        json={"remove_api_key": True, "manual_models": ["gpt-4.1-mini"]},
    )
    if removed.status_code != 200 or removed.json()["api_key_set"]:
        raise SystemExit("openai api key removal failed")

with open_database_connection() as connection:
    secret_row = connection.execute(
        "SELECT api_key_secret FROM provider_configurations WHERE provider = 'openai'"
    ).fetchone()
    run_count = connection.execute(
        "SELECT COUNT(*) AS count FROM analysis_runs"
    ).fetchone()
    profile_table = connection.execute(
        "SELECT to_regclass('analysis_profiles') AS table_name"
    ).fetchone()
if secret_row is None or secret_row["api_key_secret"] is not None:
    raise SystemExit("openai secret was not removed in storage")
if int(run_count["count"]) != 2:
    raise SystemExit("indexing runs were not persisted as expected")
if profile_table["table_name"] is not None:
    raise SystemExit("analysis profile table still exists")
print("providers_indexing_smoke=ok")
PY
