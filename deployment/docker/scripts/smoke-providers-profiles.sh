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

    project = client.post("/api/projects", headers=headers, json={"name": "Profiles"})
    if project.status_code != 201:
        raise SystemExit("project creation failed")
    project_id = project.json()["id"]

    local_profile = client.post(
        f"/api/projects/{project_id}/analysis-profiles",
        headers=headers,
        json={
            "name": "Local profile",
            "provider": "vllm",
            "model": "local-embed",
            "thresholds": {"similarity": 0.78},
            "algorithm_settings": {
                "algorithm": "hdbscan",
                "min_cluster_size": 5,
                "cluster_selection_epsilon": 0,
            },
        },
    )
    if local_profile.status_code != 201:
        raise SystemExit(f"local profile creation failed: {local_profile.text}")
    if local_profile.json()["is_cloud_provider"]:
        raise SystemExit("vllm profile was marked as cloud")

    cloud_profile = client.post(
        f"/api/projects/{project_id}/analysis-profiles",
        headers=headers,
        json={
            "name": "Cloud profile",
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "thresholds": {"similarity": 0.82},
            "algorithm_settings": {
                "algorithm": "agglomerative",
                "n_clusters": 2,
                "linkage": "ward",
            },
        },
    )
    if cloud_profile.status_code != 201:
        raise SystemExit(f"cloud profile creation failed: {cloud_profile.text}")
    if not cloud_profile.json()["is_cloud_provider"]:
        raise SystemExit("openai profile was not marked as cloud")

    profiles = client.get(
        f"/api/projects/{project_id}/analysis-profiles", headers=headers
    )
    if profiles.status_code != 200 or len(profiles.json()) != 2:
        raise SystemExit("profiles were not persisted")

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
    profile_count = connection.execute(
        "SELECT COUNT(*) AS count FROM analysis_profiles"
    ).fetchone()
if secret_row is None or secret_row["api_key_secret"] is not None:
    raise SystemExit("openai secret was not removed in storage")
if int(profile_count["count"]) != 2:
    raise SystemExit("analysis profiles were not persisted as expected")
print("providers_profiles_smoke=ok")
PY
