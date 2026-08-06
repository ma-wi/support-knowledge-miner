#!/usr/bin/env bats

setup() {
  REPOSITORY_ROOT="$(cd "${BATS_TEST_DIRNAME}/../.." && pwd)"
  export REPOSITORY_ROOT
  export FAKE_DOCKER_LOG="${BATS_TEST_TMPDIR}/docker.log"
  export FAKE_SLEEP_LOG="${BATS_TEST_TMPDIR}/sleep.log"
  export FAKE_UV_LOG="${BATS_TEST_TMPDIR}/uv.log"
  export FAKE_UV_PAYLOAD_LOG="${BATS_TEST_TMPDIR}/uv-payload.log"
  export PATH="${BATS_TEST_DIRNAME}/fixtures/bin:${PATH}"
}

assert_contains() {
  local file="$1"
  local expected="$2"

  grep -F -- "${expected}" "${file}"
}

assert_occurrences() {
  local expected_count="$1"
  local pattern="$2"
  local file="$3"
  local actual_count

  actual_count="$(grep -F -c -- "${pattern}" "${file}" || true)"
  [[ "${actual_count}" -eq "${expected_count}" ]]
}

run_smoke_script() {
  local script_name="$1"
  shift

  run env "$@" bash \
    "${REPOSITORY_ROOT}/deployment/docker/scripts/${script_name}"
}

@test "all Docker smoke scripts execute their isolated Compose lifecycle and Python contract" {
  local -a cases=(
    "smoke-auth-users.sh|auth-project|56101|auth_users_audit_smoke=ok"
    "smoke-imports.sh|imports-project|56102|imports_smoke=ok"
    "smoke-postgres.sh|postgres-project|56103|smoke_persistence_marker"
    "smoke-projects.sh|projects-project|56104|project_lifecycle_smoke=ok"
    "smoke-providers-profiles.sh|providers-project|56105|providers_indexing_smoke=ok"
  )
  local case_value script_name project_name port payload_marker

  for case_value in "${cases[@]}"; do
    IFS="|" read -r script_name project_name port payload_marker <<<"${case_value}"
    : >"${FAKE_DOCKER_LOG}"
    : >"${FAKE_UV_LOG}"
    : >"${FAKE_UV_PAYLOAD_LOG}"

    run_smoke_script \
      "${script_name}" \
      "SKM_SMOKE_PROJECT_NAME=${project_name}" \
      "SKM_SMOKE_POSTGRES_PORT=${port}"

    [[ "${status}" -eq 0 ]]
    assert_contains "${FAKE_DOCKER_LOG}" \
      "POSTGRES_PORT=${port} | docker compose -p ${project_name} -f "
    assert_contains "${FAKE_DOCKER_LOG}" " up -d"
    assert_contains "${FAKE_DOCKER_LOG}" " down -v"
    assert_contains "${FAKE_UV_LOG}" "args=run --locked python -"
    assert_contains "${FAKE_UV_LOG}" \
      "SKM_DATABASE_URL=postgresql://support_knowledge_miner:support_knowledge_miner_dev_password@localhost:${port}/support_knowledge_miner"
    assert_contains "${FAKE_UV_PAYLOAD_LOG}" "${payload_marker}"
  done
}

@test "PostgreSQL smoke verifies persistence after a real restart boundary" {
  run_smoke_script \
    "smoke-postgres.sh" \
    "SKM_SMOKE_PROJECT_NAME=persistence-project" \
    "SKM_SMOKE_POSTGRES_PORT=56110"

  [[ "${status}" -eq 0 ]]
  assert_occurrences 1 " restart postgres" "${FAKE_DOCKER_LOG}"
  assert_occurrences 2 "args=run --locked python -" "${FAKE_UV_LOG}"
  assert_contains "${FAKE_UV_PAYLOAD_LOG}" "before_restart"
  assert_contains "${FAKE_UV_PAYLOAD_LOG}" "database state did not persist across restart"
}

@test "migration smoke passes separate fresh and upgrade databases to its payload" {
  run_smoke_script \
    "smoke-migrations.sh" \
    "SKM_MIGRATION_SMOKE_PROJECT_NAME=migration-project" \
    "SKM_MIGRATION_SMOKE_POSTGRES_PORT=56111"

  [[ "${status}" -eq 0 ]]
  assert_contains "${FAKE_DOCKER_LOG}" \
    "docker compose -p migration-project -f "
  assert_contains "${FAKE_DOCKER_LOG}" \
    "createdb -U support_knowledge_miner support_knowledge_miner_upgrade"
  assert_contains "${FAKE_UV_LOG}" \
    "FRESH_DATABASE_URL=postgresql://support_knowledge_miner:support_knowledge_miner_dev_password@localhost:56111/support_knowledge_miner"
  assert_contains "${FAKE_UV_LOG}" \
    "UPGRADE_DATABASE_URL=postgresql://support_knowledge_miner:support_knowledge_miner_dev_password@localhost:56111/support_knowledge_miner_upgrade"
  assert_contains "${FAKE_UV_PAYLOAD_LOG}" \
    "fresh_and_0009_to_0018_migrations=ok"
}

@test "readiness exhaustion fails closed, skips Python, and removes Compose resources" {
  export FAKE_DOCKER_FAIL_MATCH="pg_isready"
  export FAKE_DOCKER_FAIL_STATUS=42

  run_smoke_script \
    "smoke-projects.sh" \
    "SKM_SMOKE_PROJECT_NAME=not-ready-project" \
    "SKM_SMOKE_POSTGRES_PORT=56112"

  [[ "${status}" -eq 42 ]]
  assert_occurrences 31 "pg_isready" "${FAKE_DOCKER_LOG}"
  assert_occurrences 30 "sleep 1" "${FAKE_SLEEP_LOG}"
  assert_contains "${FAKE_DOCKER_LOG}" " down -v"
  [[ ! -s "${FAKE_UV_LOG}" ]]
}

@test "a failed application smoke still cleans up its database volume" {
  export FAKE_UV_STATUS=23

  run_smoke_script \
    "smoke-imports.sh" \
    "SKM_SMOKE_PROJECT_NAME=failing-import-project" \
    "SKM_SMOKE_POSTGRES_PORT=56113"

  [[ "${status}" -eq 23 ]]
  assert_contains "${FAKE_UV_PAYLOAD_LOG}" "injected batch failure"
  assert_contains "${FAKE_DOCKER_LOG}" " down -v"
}
