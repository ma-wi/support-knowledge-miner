#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/../compose.yml"
PROJECT_NAME="${SKM_SMOKE_PROJECT_NAME:-skm-t002-smoke}"
POSTGRES_PORT="${SKM_SMOKE_POSTGRES_PORT:-55433}"
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
from backend.auth import AuthService
from backend.db import run_migrations
from backend.db.connection import open_database_connection
from backend.users import CreateUserInput, UpdateUserInput, UserService

run_migrations()
auth = AuthService()
seeded = auth.seed_initial_user_from_env()
if seeded is None or seeded.email != "owner@example.test":
    raise SystemExit("initial user was not seeded")
if auth.seed_initial_user_from_env() is not None:
    raise SystemExit("initial user seed was not one-time")

token = auth.sign_in("owner@example.test", "owner-password")
if token.user.email != "owner@example.test" or not token.access_token:
    raise SystemExit("sign-in failed")
current = auth.authenticate_token(token.access_token)
users = UserService()
other = users.create_user(
    CreateUserInput(
        username="curator@example.test",
        first_name="Support",
        last_name="Curator",
        email="curator@example.test",
        password="curator-password",
    ),
    actor_user_id=current.id,
)
users.update_user(
    other.id,
    UpdateUserInput(first_name="Knowledge"),
    actor_user_id=current.id,
)
users.set_password(other.id, "changed-password", actor_user_id=current.id)
try:
    users.delete_user(current.id, actor_user_id=current.id)
except ValueError:
    pass
else:
    raise SystemExit("self-delete was allowed")
users.delete_user(other.id, actor_user_id=current.id)

with open_database_connection() as connection:
    owner_row = connection.execute(
        "SELECT password_hash FROM users WHERE email = 'owner@example.test'"
    ).fetchone()
    if owner_row is None or owner_row["password_hash"] == "owner-password":
        raise SystemExit("plaintext password was stored")
    token_rows = connection.execute("SELECT token_hash FROM user_sessions").fetchall()
    if not token_rows or any(row["token_hash"] == token.access_token for row in token_rows):
        raise SystemExit("plaintext session token was stored")
    audit_count = connection.execute("SELECT COUNT(*) AS count FROM audit_events").fetchone()
    if audit_count is None or int(audit_count["count"]) < 5:
        raise SystemExit("audit events were not persisted")
print("auth_users_audit_smoke=ok")
PY
