# Task T001: Local runtime, PostgreSQL/pgvector, migrations, and backend health

- Status: reviewed
- Parent requirement: support-knowledge-miner-mvp1
- Plan: `.ai/work/support-knowledge-miner-mvp1/PLAN.md`
- Depends on: none
- Owner/agent: implementer
- Last updated: 2026-07-19

## Objective

Create the local Docker Compose and backend persistence foundation: PostgreSQL with pgvector, persistent volumes, schema migration path, baseline backend health, and configuration needed by later tasks.

## Scope

### In scope

- Docker Compose service for PostgreSQL with pgvector and persistent volume.
- Local configuration conventions for database connection.
- Backend database connection and migration mechanism.
- Initial schema foundation for users/projects/audit-capable future tables where needed.
- Backend health/check endpoint or service check sufficient for local smoke tests.
- Tests proving pgvector availability and persistence/migration basics.

### Out of scope

- Auth UI and user CRUD behavior.
- Project lifecycle behavior beyond schema support.
- vLLM/OpenAI provider functionality.
- Clustering/embedding implementation.

## Preconditions

- Specification is `ready-for-implementation`.
- ADR-0002 and ADR-0004 are accepted.

## Affected files or components

- Docker Compose/config files.
- Backend database/migration/config modules.
- Backend tests.
- Local setup documentation if needed.

## Acceptance criteria

- [x] Spec AC-17: Docker Compose starts PostgreSQL with pgvector using a persistent volume.
- [x] Database migrations can initialize the schema from an empty database.
- [x] Tests verify pgvector extension availability.
- [x] Backend can connect to the database through local configuration.

## Implementation constraints

- Do not connect to production or external databases.
- Do not commit local secrets or generated credentials.
- Use deterministic migrations; do not rely on manual database edits.

## Applicable specification and test seam

- Specification criteria: AC-17.
- Primary observable boundary for this task: backend database/migration and local runtime smoke boundary.
- Implementation-specific boundaries to avoid testing directly: private connection helper internals.

## Verification

- [x] Focused tests
- [x] Relevant linting and static analysis
- [x] Security or dependency checks when applicable
- [x] Documentation assessment

Exact commands:

```bash
./.ai/tools/test.sh
./.ai/tools/lint.sh
python .ai/tools/check-docs.py
```

## Risks or blockers

- pgvector image/version choice may require dependency review.
- Local Docker availability may vary.

## Result

Implemented a local PostgreSQL/pgvector foundation:

- Added Docker Compose assets under `deployment/docker/` with a local
  `pgvector/pgvector:pg17` PostgreSQL service, healthcheck, and persistent named
  volume.
- Added local database configuration constrained to local Docker/test hosts.
- Added PostgreSQL connection, deterministic SQL migration runner, packaged SQL
  migrations, and database health check service seam.
- Added foundation migration enabling pgvector and creating baseline
  `app_metadata`.
- Added tests for local database URL validation, Compose pgvector/persistence
  configuration, migration ordering/content, and health model behavior.
- Added `deployment/docker/scripts/smoke-postgres.sh` to start an isolated local
  PostgreSQL/pgvector Compose project, apply migrations to an empty database,
  verify pgvector through the backend health query, restart PostgreSQL, verify
  state persisted across restart, and clean up the test project.
- Added optional vLLM Compose profiles and runtime documentation for the accepted
  local model-provider path: `vllm-gpu` for GPU-default use and `vllm-cpu` for
  CPU fallback. These profiles are not started by mandatory tests because they
  may download large model/runtime images.
- Added `psycopg[binary]>=3.2,<4` as the PostgreSQL driver. Standard library has
  no PostgreSQL client; `psycopg` is the maintained PostgreSQL adapter, locked in
  `uv.lock`, used only for backend DB connections/migrations/health in this task,
  and replaceable behind `backend.db.connection` if needed.

Verification evidence:

- `docker compose -f deployment/docker/compose.yml config` passed.
- `docker compose --env-file deployment/docker/.env.example -f deployment/docker/compose.yml --profile vllm-gpu config` passed.
- `docker compose --env-file deployment/docker/.env.example -f deployment/docker/compose.yml --profile vllm-cpu config` passed.
- `deployment/docker/scripts/smoke-postgres.sh` passed; applied
  `0001_foundation.sql`, verified `pgvector_installed=True`, restarted
  PostgreSQL, and verified `restart_persistence=ok`.
- `./.ai/tools/test.sh` passed.
- `./.ai/tools/lint.sh` passed.
- `./.ai/tools/security.sh` passed.
- `./.ai/tools/check-dependencies.sh` passed.
- `./.ai/tools/build.sh` passed.
- `python .ai/tools/check-docs.py` passed.
- `./.ai/tools/verify.sh` passed.
- `python .ai/tools/check-work-state.py` passed.

Skipped checks: none.

Residual risks:

- The PostgreSQL smoke script removes its isolated containers, network, and
  volume. Optional vLLM profiles are syntax/config validated but not started in
  mandatory gates to avoid large model/runtime downloads and host-specific GPU
  assumptions.

Review remediation:

- Addressed P1 from `.ai/work/support-knowledge-miner-mvp1/REVIEW.md` by adding
  and executing a real local PostgreSQL/pgvector smoke script covering empty-DB
  migration, real health query, restart, and persistence.
- Addressed P2 by adding structured optional vLLM GPU/CPU Compose profiles under
  `deployment/docker/` and documenting GPU-default/CPU-fallback plus the local
  endpoint path.
