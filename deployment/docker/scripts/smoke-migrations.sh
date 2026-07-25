#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/../compose.yml"
PROJECT_NAME="${SKM_MIGRATION_SMOKE_PROJECT_NAME:-skm-migration-smoke}"
POSTGRES_PORT="${SKM_MIGRATION_SMOKE_POSTGRES_PORT:-55433}"
DB_USER="support_knowledge_miner"
DB_PASSWORD="support_knowledge_miner_dev_password"
FRESH_DB="support_knowledge_miner"
UPGRADE_DB="support_knowledge_miner_upgrade"
FRESH_DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@localhost:${POSTGRES_PORT}/${FRESH_DB}"
UPGRADE_DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@localhost:${POSTGRES_PORT}/${UPGRADE_DB}"

run_compose() {
  POSTGRES_DB="${FRESH_DB}" \
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
    pg_isready -U "${DB_USER}" -d "${FRESH_DB}" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

run_compose exec -T postgres createdb -U "${DB_USER}" "${UPGRADE_DB}"

FRESH_DATABASE_URL="${FRESH_DATABASE_URL}" \
  UPGRADE_DATABASE_URL="${UPGRADE_DATABASE_URL}" \
  uv run --locked python - <<'PY'
from importlib import resources
import os
from uuid import UUID, uuid4

from psycopg.errors import CheckViolation

from backend.auth.passwords import hash_password
from backend.auth.service import AuthService
from backend.config import DatabaseSettings
from backend.db.connection import open_database_connection
from backend.db.migrate import _SCHEMA_TABLE_SQL, _migration_files, run_migrations


def settings(name: str) -> DatabaseSettings:
    return DatabaseSettings(url=os.environ[name])


def assert_provider_constraints(database: DatabaseSettings, user_id: UUID) -> None:
    project_id = uuid4()
    import_id = uuid4()
    dataset_id = uuid4()
    profile_id = uuid4()
    with open_database_connection(database) as connection:
        connection.execute(
            "INSERT INTO projects (id, name, created_by_user_id) VALUES (%s, %s, %s)",
            (project_id, "Migration smoke", user_id),
        )
        connection.execute(
            """
            INSERT INTO import_logs (
                id, project_id, source_type, source_name, status, total_records,
                valid_records, created_by_user_id
            )
            VALUES (%s, %s, 'csv', 'migration.csv', 'completed', 1, 1, %s)
            """,
            (import_id, project_id, user_id),
        )
        connection.execute(
            """
            INSERT INTO dataset_versions (
                id, project_id, version_number, import_log_id, record_count,
                source_type, source_name, created_by_user_id
            )
            VALUES (%s, %s, 1, %s, 1, 'csv', 'migration.csv', %s)
            """,
            (dataset_id, project_id, import_id, user_id),
        )
        connection.execute(
            """
            INSERT INTO analysis_profiles (
                id, project_id, name, provider, model, is_cloud_provider,
                created_by_user_id
            )
            VALUES (%s, %s, 'Ollama', 'ollama', 'local-model', false, %s)
            """,
            (profile_id, project_id, user_id),
        )
        connection.execute(
            """
            INSERT INTO provider_configurations (provider, manual_models)
            VALUES ('ollama', '["local-model"]'::jsonb)
            """
        )
        connection.execute(
            """
            INSERT INTO analysis_runs (
                id, project_id, dataset_version_id, analysis_profile_id, status,
                profile_snapshot, provider, model, created_by_user_id
            )
            VALUES (%s, %s, %s, %s, 'queued', '{}'::jsonb, 'ollama',
                    'local-model', %s)
            """,
            (uuid4(), project_id, dataset_id, profile_id, user_id),
        )
        for table, statement in (
            (
                "provider_configurations",
                """
                INSERT INTO provider_configurations (provider)
                VALUES ('unsupported')
                """,
            ),
            (
                "analysis_profiles",
                """
                INSERT INTO analysis_profiles (
                    id, project_id, name, provider, model, is_cloud_provider
                )
                VALUES (%s, %s, 'Invalid', 'unsupported', 'model', false)
                """,
            ),
            (
                "analysis_runs",
                """
                INSERT INTO analysis_runs (
                    id, project_id, dataset_version_id, analysis_profile_id,
                    status, profile_snapshot, provider, model
                )
                VALUES (%s, %s, %s, %s, 'queued', '{}'::jsonb,
                        'unsupported', 'model')
                """,
            ),
        ):
            parameters = {
                "provider_configurations": (),
                "analysis_profiles": (uuid4(), project_id),
                "analysis_runs": (uuid4(), project_id, dataset_id, profile_id),
            }[table]
            try:
                with connection.transaction():
                    connection.execute(statement, parameters)
            except CheckViolation:
                pass
            else:
                raise AssertionError(f"{table} accepted an unsupported provider")
        connection.commit()


fresh = settings("FRESH_DATABASE_URL")
fresh_result = run_migrations(fresh)
if "0011_email_identity.sql" not in fresh_result.applied_versions:
    raise AssertionError("fresh migration did not apply email identity migration")
fresh_user_id = uuid4()
with open_database_connection(fresh) as connection:
    connection.execute(
        """
        INSERT INTO users (id, first_name, last_name, email, password_hash)
        VALUES (%s, 'Fresh', 'User', 'fresh@example.test', %s)
        """,
        (fresh_user_id, hash_password("fresh-password")),
    )
    connection.commit()
assert_provider_constraints(fresh, fresh_user_id)

upgrade = settings("UPGRADE_DATABASE_URL")
with open_database_connection(upgrade) as connection:
    with connection.transaction():
        connection.execute(_SCHEMA_TABLE_SQL)
        for path in _migration_files():
            if path.name > "0009_exports.sql":
                continue
            connection.execute(path.read_text(encoding="utf-8"))
            connection.execute(
                "INSERT INTO schema_migrations (version) VALUES (%s)",
                (path.name,),
            )
        for table, constraint in (
            ("provider_configurations", "provider_configurations_provider_check"),
            ("analysis_profiles", "analysis_profiles_provider_check"),
            ("analysis_runs", "analysis_runs_provider_check"),
        ):
            connection.execute(
                f"ALTER TABLE {table} DROP CONSTRAINT {constraint}"
            )
            connection.execute(
                f"""
                ALTER TABLE {table}
                ADD CONSTRAINT {constraint}
                CHECK (provider IN ('openai', 'vllm'))
                """
            )
        first_user_id = UUID("11111111-1111-1111-1111-111111111111")
        second_user_id = UUID("22222222-2222-2222-2222-222222222222")
        connection.execute(
            """
            INSERT INTO users (
                id, username, first_name, last_name, email, password_hash
            )
            VALUES
                (%s, 'user-b@example.test', 'Legacy', 'A',
                 'user-a@example.test', %s),
                (%s, 'legacy-b', 'Legacy', 'B',
                 'user-b@example.test', %s)
            """,
            (
                first_user_id,
                hash_password("user-a-password"),
                second_user_id,
                hash_password("user-b-password"),
            ),
        )

upgrade_result = run_migrations(upgrade)
if upgrade_result.applied_versions != (
    "0010_ollama_provider.sql",
    "0011_email_identity.sql",
):
    raise AssertionError(f"unexpected upgrade set: {upgrade_result.applied_versions}")
with open_database_connection(upgrade) as connection:
    username_column = connection.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'users'
          AND column_name = 'username'
        """
    ).fetchone()
if username_column is not None:
    raise AssertionError("legacy username column remains after upgrade")
token = AuthService(upgrade).sign_in("user-b@example.test", "user-b-password")
if token.user.id != second_user_id:
    raise AssertionError("email login resolved the wrong legacy account")
assert_provider_constraints(upgrade, second_user_id)
print("fresh_and_0009_upgrade_migrations=ok")
PY
