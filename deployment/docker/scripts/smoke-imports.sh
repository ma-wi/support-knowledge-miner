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

run_compose up -d --wait --wait-timeout 30 postgres

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
from pathlib import Path
from tempfile import TemporaryDirectory
from time import sleep

from psycopg import OperationalError
from fastapi.testclient import TestClient

import backend.api.app as api_app_module
import backend.imports.service as import_service_module
from backend.api import create_app
from backend.db import run_migrations
from backend.db.connection import open_database_connection
from backend.imports import ImportService

for attempt in range(30):
    try:
        run_migrations()
        break
    except OperationalError:
        if attempt == 29:
            raise
        sleep(1)

class SmokeImportService(ImportService):
    fail_batches = False
    batch_calls = 0

    def _insert_message_batch(self, connection, values):
        super()._insert_message_batch(connection, values)
        if self.fail_batches:
            self.batch_calls += 1
            if self.batch_calls == 2:
                raise RuntimeError("injected batch failure")


import_service_module.DATABASE_BATCH_SIZE = 2
import_service_module.DATABASE_BATCH_BYTES = 1024
import_service = SmokeImportService()

with TemporaryDirectory(prefix="skm-import-smoke-") as temp_directory:
  api_app_module.tempfile.tempdir = temp_directory
  with TestClient(
      create_app(import_service=import_service),
      raise_server_exceptions=False,
  ) as client:
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

    def raw_import(filename, media_type, content):
        return client.post(
            f"/api/projects/{project_id}/imports",
            headers={
                **headers,
                "Content-Type": media_type,
                "Content-Disposition": (
                    f"attachment; filename*=UTF-8''{filename}"
                ),
            },
            content=content.encode("utf-8"),
        )

    csv_import = raw_import(
        "fixture.csv",
        "text/csv",
        (
            "ticket_id,message_group_id,message,answer\n"
            "T-1,G-1,Hello,Answer\n"
            "T-1,G-1,Duplicate,Answer 2\n"
            "T-2,G-2, ,Missing message\n"
            "T-3,G-3,Third,Answer 3\n"
            "T-4,G-4,Fourth,Answer 4\n"
        ),
    )
    if csv_import.status_code != 201:
        raise SystemExit(f"csv import failed: {csv_import.status_code}")
    csv_payload = csv_import.json()
    if csv_payload["log"]["valid_records"] != 4:
        raise SystemExit("csv valid count mismatch")
    if csv_payload["log"]["skipped_records"] != 1:
        raise SystemExit("csv skipped count mismatch")
    if csv_payload["dataset_version"] is None:
        raise SystemExit("csv import did not create dataset version")

    bad_headers = raw_import(
        "bad.csv",
        "text/csv",
        "ticket_id,message,answer\nT-1,Hi,A\n",
    )
    if bad_headers.status_code != 201:
        raise SystemExit("missing-header import did not create log response")
    if bad_headers.json()["dataset_version"] is not None:
        raise SystemExit("missing-header import created dataset version")
    if bad_headers.json()["log"]["status"] != "failed":
        raise SystemExit("missing-header import was not failed")

    legacy_headers = raw_import(
        "legacy.csv",
        "text/csv",
        (
            "ticketid,messagegroupid,message,answer\n"
            "T-1,G-1,Hi,A\n"
        ),
    )
    if legacy_headers.status_code != 201:
        raise SystemExit("legacy-header import did not create log response")
    if legacy_headers.json()["dataset_version"] is not None:
        raise SystemExit("legacy-header import created dataset version")
    if legacy_headers.json()["log"]["failure_reason"] != (
        "CSV-Kopfzeilen fehlen: ticket_id, message_group_id."
    ):
        raise SystemExit("legacy-header import failed for the wrong reason")

    json_import = raw_import(
        "fixture.json",
        "application/json",
        '[{"ticket_id":"J-1","message_group_id":"G-1","message":"Hi","answer":"A"}]',
    )
    if json_import.status_code != 201 or json_import.json()["log"]["valid_records"] != 1:
        raise SystemExit("json import failed")

    logs = client.get(f"/api/projects/{project_id}/imports", headers=headers)
    if logs.status_code != 200 or len(logs.json()) != 4:
        raise SystemExit("import logs were not persisted")

    import_service.fail_batches = True
    rollback_import = raw_import(
        "rollback.csv",
        "text/csv",
        (
            "ticket_id,message_group_id,message,answer\n"
            "R-1,R-1,One,Answer\n"
            "R-2,R-2,Two,Answer\n"
            "R-3,R-3,Three,Answer\n"
        ),
    )
    if rollback_import.status_code != 500:
        raise SystemExit("injected persistence failure was not surfaced")

  if list(Path(temp_directory).iterdir()):
      raise SystemExit("temporary import file was not removed")

with open_database_connection() as connection:
    pair_count = connection.execute("SELECT COUNT(*) AS count FROM message_pairs").fetchone()
    log_count = connection.execute("SELECT COUNT(*) AS count FROM import_logs").fetchone()
if int(pair_count["count"]) != 5:
    raise SystemExit("message pairs were not persisted as expected")
if int(log_count["count"]) != 4:
    raise SystemExit("import logs were not persisted as expected")
print("imports_smoke=ok")
PY
