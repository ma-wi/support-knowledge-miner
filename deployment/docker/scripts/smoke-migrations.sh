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

run_compose up -d --wait --wait-timeout 30 postgres

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


def assert_indexing_provider_constraints(database: DatabaseSettings, user_id: UUID) -> UUID:
    project_id = uuid4()
    import_id = uuid4()
    dataset_id = uuid4()
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
                source_type, source_name, display_name, created_by_user_id
            )
            VALUES (
                %s, %s, 1, %s, 1, 'csv', 'migration.csv',
                'Migration fixture', %s
            )
            """,
            (dataset_id, project_id, import_id, user_id),
        )
        connection.execute(
            """
            INSERT INTO provider_configurations (
                id, provider, display_name, manual_models, available_models,
                embedding_models, llm_models
            )
            VALUES (
                %s, 'ollama', 'Ollama', '["local-model"]'::jsonb,
                '["local-model"]'::jsonb, '["local-model"]'::jsonb,
                '[]'::jsonb
            )
            """,
            (uuid4(),),
        )
        connection.execute(
            """
            INSERT INTO analysis_runs (
                id, project_id, dataset_version_id, status, provider, model,
                parameters, created_by_user_id
            )
            VALUES (%s, %s, %s, 'queued', 'ollama', 'local-model',
                    '{}'::jsonb, %s)
            """,
            (uuid4(), project_id, dataset_id, user_id),
        )
        for table, statement in (
            (
                "provider_configurations",
                """
                INSERT INTO provider_configurations (id, provider, display_name)
                VALUES (%s, 'unsupported', 'Unsupported')
                """,
            ),
            (
                "analysis_runs",
                """
                INSERT INTO analysis_runs (
                    id, project_id, dataset_version_id, status, provider, model
                )
                VALUES (%s, %s, %s, 'queued', 'unsupported', 'model')
                """,
            ),
        ):
            parameters = {
                "provider_configurations": (uuid4(),),
                "analysis_runs": (uuid4(), project_id, dataset_id),
            }[table]
            try:
                with connection.transaction():
                    connection.execute(statement, parameters)
            except CheckViolation:
                pass
            else:
                raise AssertionError(f"{table} accepted an unsupported provider")
        connection.commit()
    return project_id


def assert_project_cluster_budget_defaults(
    database: DatabaseSettings, project_id: UUID
) -> None:
    with open_database_connection(database) as connection:
        row = connection.execute(
            """
            SELECT llm_taxonomy_max_source_clusters,
                   llm_taxonomy_max_prompt_characters,
                   llm_taxonomy_max_total_keyword_terms
            FROM projects
            WHERE id = %s
            """,
            (project_id,),
        ).fetchone()
    if row is None:
        raise AssertionError("project cluster budget fixture is unavailable")
    actual = (
        row["llm_taxonomy_max_source_clusters"],
        row["llm_taxonomy_max_prompt_characters"],
        row["llm_taxonomy_max_total_keyword_terms"],
    )
    if actual != (200, 80_000, 250_000):
        raise AssertionError(f"unexpected project cluster budget defaults: {actual}")
    budget_ranges = (
        ("llm_taxonomy_max_source_clusters", 1, 500),
        ("llm_taxonomy_max_prompt_characters", 10_000, 500_000),
        ("llm_taxonomy_max_total_keyword_terms", 1_000, 1_000_000),
    )
    for column, minimum, maximum in budget_ranges:
        for value in (minimum, maximum):
            with open_database_connection(database) as connection:
                with connection.transaction():
                    connection.execute(
                        f"UPDATE projects SET {column} = %s WHERE id = %s",
                        (value, project_id),
                    )
        for value in (minimum - 1, maximum + 1):
            try:
                with open_database_connection(database) as connection:
                    with connection.transaction():
                        connection.execute(
                            f"UPDATE projects SET {column} = %s WHERE id = %s",
                            (value, project_id),
                        )
            except CheckViolation:
                pass
            else:
                raise AssertionError(
                    f"project cluster budget accepted {column}={value}"
                )
    with open_database_connection(database) as connection:
        with connection.transaction():
            connection.execute(
                """
                UPDATE projects
                SET llm_taxonomy_max_source_clusters = 200,
                    llm_taxonomy_max_prompt_characters = 80000,
                    llm_taxonomy_max_total_keyword_terms = 250000
                WHERE id = %s
                """,
                (project_id,),
            )


def assert_import_source_id_columns(database: DatabaseSettings) -> None:
    with open_database_connection(database) as connection:
        columns = {
            str(row["column_name"])
            for row in connection.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = 'message_pairs'
                """
            ).fetchall()
        }
    if not {"ticket_id", "message_group_id"}.issubset(columns):
        raise AssertionError(f"snake-case import columns missing: {columns}")
    if {"ticketid", "messagegroupid"} & columns:
        raise AssertionError(f"legacy import columns remain: {columns}")


def assert_profile_free_indexing_schema(
    database: DatabaseSettings, legacy_run_id: UUID | None = None
) -> None:
    with open_database_connection(database) as connection:
        profile_table = connection.execute(
            "SELECT to_regclass('analysis_profiles') AS table_name"
        ).fetchone()["table_name"]
        run_columns = {
            str(row["column_name"])
            for row in connection.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = 'analysis_runs'
                """
            ).fetchall()
        }
        if legacy_run_id is None:
            run = None
        else:
            run = connection.execute(
                "SELECT id FROM analysis_runs WHERE id = %s",
                (legacy_run_id,),
            ).fetchone()
    if profile_table is not None:
        raise AssertionError("analysis_profiles table remains")
    if {"analysis_profile_id", "profile_snapshot"} & run_columns:
        raise AssertionError(f"profile-coupled run columns remain: {run_columns}")
    required_columns = {
        "dataset_version_id",
        "provider",
        "model",
        "parameters",
        "phase",
        "error_code",
        "cancel_requested_at",
        "deleted_at",
        "deleted_by_user_id",
    }
    if not required_columns.issubset(run_columns):
        raise AssertionError(f"indexing run columns missing: {run_columns}")
    if legacy_run_id is not None and run is not None:
        raise AssertionError("legacy derived analysis run survived destructive migration")


fresh = settings("FRESH_DATABASE_URL")
fresh_result = run_migrations(fresh)
if not {
    "0012_import_snake_case_fields.sql",
    "0013_remove_prompt_identifier_run_mode.sql",
    "0014_indexing_runs_without_profiles.sql",
}.issubset(fresh_result.applied_versions):
    raise AssertionError("fresh migration did not apply the latest migrations")
assert_import_source_id_columns(fresh)
assert_profile_free_indexing_schema(fresh)
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
fresh_project_id = assert_indexing_provider_constraints(fresh, fresh_user_id)
assert_project_cluster_budget_defaults(fresh, fresh_project_id)

upgrade = settings("UPGRADE_DATABASE_URL")
legacy_run_id = uuid4()
with open_database_connection(
    upgrade, register_pgvector_types=False
) as connection:
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
        legacy_project_id = uuid4()
        legacy_import_id = uuid4()
        legacy_dataset_id = uuid4()
        legacy_profile_id = uuid4()
        connection.execute(
            "INSERT INTO projects (id, name) VALUES (%s, 'Legacy project')",
            (legacy_project_id,),
        )
        connection.execute(
            """
            INSERT INTO import_logs (
                id, project_id, source_type, source_name, status, total_records,
                valid_records
            )
            VALUES (%s, %s, 'csv', 'legacy.csv', 'completed', 1, 1)
            """,
            (legacy_import_id, legacy_project_id),
        )
        connection.execute(
            """
            INSERT INTO dataset_versions (
                id, project_id, version_number, import_log_id, record_count,
                source_type, source_name
            )
            VALUES (%s, %s, 1, %s, 1, 'csv', 'legacy.csv')
            """,
            (legacy_dataset_id, legacy_project_id, legacy_import_id),
        )
        connection.execute(
            """
            INSERT INTO analysis_profiles (
                id, project_id, name, provider, model, is_cloud_provider,
                prompt_identifier, prompt_template
            )
            VALUES (%s, %s, 'Legacy profile', 'vllm', 'local-model', false,
                    'faq-v1', 'retained')
            """,
            (legacy_profile_id, legacy_project_id),
        )
        connection.execute(
            """
            INSERT INTO analysis_runs (
                id, project_id, dataset_version_id, analysis_profile_id, status,
                profile_snapshot, provider, model, parameters
            )
            VALUES (
                %s, %s, %s, %s, 'queued',
                '{"name": "Legacy profile", "prompt_identifier": "faq-v1",
                  "prompt_template": "retained"}'::jsonb,
                'vllm', 'local-model',
                '{"mode": "fixture", "cloud_use_confirmed": true}'::jsonb
            )
            """,
            (
                legacy_run_id,
                legacy_project_id,
                legacy_dataset_id,
                legacy_profile_id,
            ),
        )

upgrade_result = run_migrations(upgrade)
if upgrade_result.applied_versions != (
    "0010_ollama_provider.sql",
    "0011_email_identity.sql",
    "0012_import_snake_case_fields.sql",
    "0013_remove_prompt_identifier_run_mode.sql",
    "0014_indexing_runs_without_profiles.sql",
    "0015_cluster_sets_llm_summaries.sql",
    "0016_explorer_exports.sql",
    "0017_provider_instances_and_global_jobs.sql",
    "0018_provider_available_models.sql",
    "0019_project_ticket_url_template.sql",
    "0020_cluster_keywords_and_fixed_status.sql",
    "0021_project_cluster_budget_settings.sql",
):
    raise AssertionError(f"unexpected upgrade set: {upgrade_result.applied_versions}")
assert_import_source_id_columns(upgrade)
assert_profile_free_indexing_schema(upgrade, legacy_run_id)
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
assert_indexing_provider_constraints(upgrade, second_user_id)
assert_project_cluster_budget_defaults(upgrade, legacy_project_id)
print("fresh_and_0009_to_0021_migrations=ok")
PY
