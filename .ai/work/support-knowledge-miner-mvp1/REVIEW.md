# Review: support-knowledge-miner-mvp1

- Reviewer: Codex
- Date: 2026-07-22
- Scope reviewed: T001 remediation after prior `REQUEST_CHANGES`; later tasks remain `ready` and were not reviewed for implementation completeness.
- Verdict: APPROVE

## Findings

No blocking or material findings remain for T001.

## Prior Findings Rechecked

### P1: T001 marked verified without real database/runtime behavior

- Previous status: REQUEST_CHANGES
- Current status: resolved
- Evidence: `deployment/docker/scripts/smoke-postgres.sh` now starts an isolated local PostgreSQL/pgvector Compose project, applies migrations to an empty database, verifies pgvector through `check_database_health()`, restarts PostgreSQL, and verifies persisted state via `smoke_persistence_marker`.
- Reviewer verification: `deployment/docker/scripts/smoke-postgres.sh` passed on 2026-07-22 with `applied=('0001_foundation.sql',) pgvector_installed=True` and `restart_persistence=ok pgvector_installed=True`.

### P2: Docker Compose lacked accepted vLLM path / CPU fallback documentation

- Previous status: REQUEST_CHANGES
- Current status: resolved
- Evidence: `deployment/docker/compose.yml` now defines optional `vllm-gpu` and `vllm-cpu` profiles with persistent `vllm-cache`; `deployment/docker/README.md` documents GPU-default and CPU-fallback commands and the local OpenAI-compatible endpoint.
- Reviewer verification: Compose config validation passed for base, `vllm-gpu`, and `vllm-cpu` profiles on 2026-07-22.

## Verification Observed

- `docker compose -f deployment/docker/compose.yml config`: PASS
- `docker compose --env-file deployment/docker/.env.example -f deployment/docker/compose.yml --profile vllm-gpu config`: PASS
- `docker compose --env-file deployment/docker/.env.example -f deployment/docker/compose.yml --profile vllm-cpu config`: PASS
- `deployment/docker/scripts/smoke-postgres.sh`: PASS
- `./.ai/tools/test.sh`: PASS as part of focused gate batch and full verify
- `./.ai/tools/lint.sh`: PASS as part of focused gate batch and full verify
- `./.ai/tools/security.sh`: PASS as part of focused gate batch and full verify
- `./.ai/tools/check-dependencies.sh`: PASS as part of focused gate batch and full verify
- `./.ai/tools/build.sh`: PASS as part of focused gate batch and full verify
- `python .ai/tools/check-docs.py`: PASS
- `python .ai/tools/check-work-state.py`: PASS
- `./.ai/tools/verify.sh`: PASS

## Notes

- Optional vLLM profiles were configuration-validated but not started. This is acceptable for T001 because starting vLLM may download large model/runtime images and depends on host-specific GPU/runtime availability; T001 requires the accepted local model-provider path and CPU fallback documentation, not real model inference.
- T001 is approved for transition from `verified` to `reviewed`.

---

# Review: support-knowledge-miner-mvp1 T002

- Reviewer: Codex
- Date: 2026-07-22
- Scope reviewed: T002 authentication, user management, sessions, initial seed, audit foundation, and minimal protected UI. T001 was checked for regressions through full verification. T003-T010 remain `ready` and were not reviewed as implemented behavior.
- Verdict: REQUEST_CHANGES

## Findings

### P2: Frontend "sign-in" bypasses real authentication

- Location: `frontend/src/App.tsx:27`
- Evidence: `signIn()` only checks that username and password are non-empty, then calls `setCurrentUser(initialUser)`. It never calls `/api/auth/sign-in`, never validates credentials against persisted users, never stores a real bearer token, and cannot surface backend/database unavailable state. The frontend test at `frontend/src/App.test.tsx:41` enters `owner` / `owner-password`, but any non-empty values would pass.
- Impact: T002 marks AC-30 and a sign-in/user-management UI slice complete, but the UI allows protected user-management screens after an unauthenticated local state transition. This contradicts the specified UI sign-in rules for invalid credentials/backend unavailable handling and weakens the user-visible protection model, even though the backend API itself remains protected.
- Required change: Integrate the frontend sign-in gate with the backend auth API, only show protected screens after a successful authenticated response, and handle invalid credentials plus backend/database unavailable errors generically. If real API-backed UI is intentionally deferred, do not mark the UI acceptance portion complete and remove/label the local-only mock so it is not presented as protected behavior.

### P2: T002 lacks API-boundary tests for the implemented auth/user contracts

- Location: `tests/api/test_auth_api_contract.py:6`
- Evidence: The only API tests inspect OpenAPI text and route registration. They do not exercise `/api/auth/sign-in`, `/api/auth/me`, `/api/users`, password updates, missing/invalid bearer tokens, self-delete denial, or API response redaction through FastAPI. The real smoke script at `deployment/docker/scripts/smoke-auth-users.sh:61` calls `AuthService` and `UserService` directly, bypassing the API boundary that the task identifies as the primary observable seam.
- Impact: Regressions in dependency wiring, request/response validation, auth dependencies, status codes, or plaintext response exposure can pass current tests. This is material because T002's accepted criteria are user/API-visible auth and user-management behavior, not just service internals.
- Required change: Add API-level integration tests against a local/test database for successful sign-in, invalid credentials, missing/invalid token rejection, authenticated user CRUD, self-delete denial, password write-only behavior, and response models excluding password hashes/plaintext passwords.

## Verification Observed

- `./.ai/tools/test.sh`: PASS (`15` Python tests, `3` frontend tests)
- `./.ai/tools/lint.sh`: PASS
- `./.ai/tools/security.sh`: PASS
- `./.ai/tools/verify.sh`: PASS, including work-state, docs, setup, format, lint, tests, dependency policy/scans, security, and build

## Notes

- Backend service code uses parameterized database queries, Argon2 password hashing, and stores only SHA-256 hashes of high-entropy session tokens. No P0/P1 security issue was found in the reviewed backend slice.
- The passing gates do not cover the two material issues above; they should be fixed and re-reviewed before advancing T002 from `verified` to `reviewed`.

---

# Re-review: support-knowledge-miner-mvp1 T002

- Reviewer: Codex
- Date: 2026-07-22
- Scope reviewed: T002 remediation for prior P2 findings, plus focused/full verification. T003-T010 remain `ready` and were not reviewed as implemented behavior.
- Verdict: APPROVE

## Findings

No blocking or material findings remain for T002.

## Prior Findings Rechecked

### P2: Frontend "sign-in" bypasses real authentication

- Previous status: REQUEST_CHANGES
- Current status: resolved
- Evidence: `frontend/src/App.tsx` now calls `/api/auth/sign-in`, stores the returned bearer token in session state, loads `/api/users` only with `Authorization: Bearer ...`, keeps the protected user-management screen closed on rejected credentials or unavailable backend, and sends authenticated requests for create/update/password/delete actions.
- Reviewer verification: `frontend/src/App.test.tsx` now covers rejected credentials, backend-unavailable behavior, API-backed sign-in, bearer-token user loading/actions, self-delete disabled state, create, and delete behavior.

### P2: T002 lacks API-boundary tests for the implemented auth/user contracts

- Previous status: REQUEST_CHANGES
- Current status: resolved
- Evidence: `tests/api/test_auth_api_integration.py` adds FastAPI `TestClient` coverage for successful sign-in, generic invalid-credential failure, missing/invalid bearer-token rejection, authenticated user list/create/update/password/delete behavior, self-delete denial, and response redaction.
- Reviewer verification: `./.ai/tools/test.sh` passed with `19` Python tests and `4` frontend tests.

## Verification Observed

- `./.ai/tools/test.sh`: PASS (`19` Python tests, `4` frontend tests)
- `./.ai/tools/lint.sh`: PASS
- `./.ai/tools/security.sh`: PASS
- `./.ai/tools/check-dependencies.sh`: PASS
- `./.ai/tools/verify.sh`: PASS, including work-state, docs, setup, format, lint, tests, dependency policy/scans, security, and build

## Notes

- `httpx2` is now a direct dev dependency for Starlette/FastAPI `TestClient` coverage. Dependency gates passed, local package metadata confirms `httpx` is not installed, and current Starlette documentation identifies `httpx2` as the TestClient backend. No remaining supply-chain blocker was found in this review.
- T002 is approved for transition from `verified` to `reviewed`.

---

# Review: support-knowledge-miner-mvp1 T003

- Reviewer: Codex
- Date: 2026-07-22
- Scope reviewed: T003 project lifecycle and isolation, including project schema, service/API boundary, frontend project-home workflow, migration/test coverage, local PostgreSQL/FastAPI smoke, and regression verification for T001/T002.
- Verdict: APPROVE

## Findings

No blocking or material findings were found for T003.

## Acceptance Criteria Trace

- AC-1: Covered by FastAPI project lifecycle endpoints, frontend project create/open/rename/delete workflow, API tests, and `deployment/docker/scripts/smoke-projects.sh`.
- AC-2: Covered for currently implemented project-owned state by project list/open/delete behavior and smoke verification that a deleted project is not returned. Later project-owned tables/files remain explicitly deferred to T004+ and must add cascade/artifact cleanup when introduced.
- AC-16: Project create/rename/delete persist audit events with the authenticated actor; smoke verifies project audit rows.
- AC-29: The authenticated frontend exposes the project home workflow added in T003.

## Verification Observed

- `deployment/docker/scripts/smoke-projects.sh`: PASS with `project_lifecycle_smoke=ok`
- `./.ai/tools/ci-setup.sh && ./.ai/tools/test.sh`: PASS after refreshing dependencies; Python `22 passed`, frontend `5 passed`
- `./.ai/tools/lint.sh`: PASS
- `./.ai/tools/verify.sh`: first run exposed a transient frontend typecheck failure after stale local Node state; after isolated typecheck confirmation, the repeated full run completed without gate failures
- Final `./.ai/tools/verify.sh`: PASS including work-state, documentation, setup, format, lint, tests, dependency policy/scans, security, and build

## Notes

- The T003 implementation intentionally hard-deletes the project row. This is compatible with the accepted destructive-delete behavior and future project-owned tables can use database cascades or explicit artifact cleanup when those resources are introduced.
- Project isolation is currently limited to the implemented project table/API surface. The stated residual risk for later project-owned tables and files is valid and should remain enforced in T004+ reviews.
- T003 is approved for transition from `verified` to `reviewed`.

---

# Review: support-knowledge-miner-mvp1 T003

- Reviewer: Codex
- Date: 2026-07-22
- Scope reviewed: T003 project lifecycle, project API, project home UI, project migration, audit behavior, focused/full verification. T004-T010 remain `ready` and were not reviewed as implemented behavior.
- Verdict: REQUEST_CHANGES

## Findings

### P2: Project delete confirmation is not atomic with deletion

- Location: `backend/projects/service.py:136`
- Evidence: `delete_project()` reads the project and compares `confirmation_name` against `project.name`, then opens a new database connection/transaction and deletes by `id` only at `backend/projects/service.py:143`. A concurrent rename between those two steps can change the project name after the confirmation check, while the subsequent `DELETE FROM projects WHERE id = %s` still removes the project.
- Impact: Project deletion is destructive and explicitly confirmation-gated by name. With multiple equal-permission local users, a stale confirmation can delete a project whose current name no longer matches the user's confirmation. This weakens the safety prompt required by UI-04/T003 and creates a concurrency bug around destructive project lifecycle behavior.
- Required change: Make confirmation and deletion a single atomic database operation. For example, run the lookup/confirmation/delete in one transaction with `SELECT ... FOR UPDATE`, or use a single `DELETE ... WHERE id = %s AND name = %s ... RETURNING ...` and only audit/delete when the current row name matches the submitted confirmation. Add a regression test covering rename/delete mismatch at the service or API boundary.

## Verification Observed

- `./.ai/tools/test.sh`: PASS (`22` Python tests, `5` frontend tests)
- `./.ai/tools/lint.sh`: PASS
- `./.ai/tools/security.sh`: PASS
- First `./.ai/tools/verify.sh`: FAIL due local `npm ci` `ENOTEMPTY` under `frontend/node_modules/.vite/vitest/...`, leaving frontend CLI tools unavailable for later gates.
- `./.ai/tools/ci-setup.sh`: PASS on rerun after the transient npm directory failure.
- Second `./.ai/tools/verify.sh`: PASS, including work-state, docs, setup, format, lint, tests, dependency policy/scans, security, and build.

## Notes

- The project lifecycle API and UI cover create/list/open/rename/delete with authenticated calls, and the real local PostgreSQL/FastAPI smoke script exercises the normal project lifecycle path.
- T003 should remain `verified` until the P2 finding is remediated and re-reviewed.

---

# Re-review: support-knowledge-miner-mvp1 T003

- Reviewer: Codex
- Date: 2026-07-22
- Scope reviewed: T003 current code state after the prior P2 finding, with focused tests/lint/security. T004-T010 remain `ready` and were not reviewed as implemented behavior.
- Verdict: REQUEST_CHANGES

## Findings

### P2: Project delete confirmation is still not atomic with deletion

- Location: `backend/projects/service.py:136`
- Evidence: The current implementation still calls `get_project(project_id)` and compares `confirmation_name` with `project.name` before opening a separate connection/transaction for `DELETE FROM projects WHERE id = %s AND deleted_at IS NULL` at `backend/projects/service.py:143`. The delete predicate still does not include the confirmed name and no row lock keeps rename/delete from interleaving.
- Impact: A project can be renamed between confirmation and deletion, while the stale confirmation still deletes by `id`. Because project deletion is destructive and name-confirmed, this remains a material lifecycle safety bug.
- Required change: Make confirmation and delete atomic, either with a single `DELETE ... WHERE id = %s AND name = %s AND deleted_at IS NULL RETURNING name` or a single transaction using `SELECT ... FOR UPDATE` before deletion. Add a regression test that fails when the project name changes before delete is applied.

## Verification Observed

- `./.ai/tools/test.sh`: PASS (`22` Python tests, `5` frontend tests)
- `./.ai/tools/lint.sh`: PASS
- `./.ai/tools/security.sh`: PASS

## Notes

- Existing tests cover ordinary mismatch after rename through the API fake and happy-path real smoke behavior, but they do not exercise the stale-confirmation/concurrent-change gap in `ProjectService.delete_project()`.
- T003 has been set back to `verified` and should not advance to `reviewed` until the P2 finding is fixed and re-reviewed.

---

# Re-review: support-knowledge-miner-mvp1 T003 stale-confirmation remediation

- Reviewer: Codex
- Date: 2026-07-22
- Scope reviewed: T003 remediation for atomic project delete confirmation, regression test, smoke-script adjustment, focused/full verification. T004-T010 remain `ready` and were not reviewed as implemented behavior.
- Verdict: APPROVE

## Findings

No blocking or material findings remain for T003.

## Prior Finding Rechecked

### P2: Project delete confirmation is still not atomic with deletion

- Previous status: REQUEST_CHANGES
- Current status: resolved
- Evidence: `backend/projects/service.py` now performs deletion with a single transactional `DELETE FROM projects WHERE id = %s AND name = %s AND deleted_at IS NULL RETURNING name`, so the confirmed name is part of the current-row delete predicate and the audit metadata uses the returned row name.
- Reviewer verification: `tests/projects/test_project_service.py` adds a regression test that fails if deletion can proceed without the confirmed current project name. Focused and full verification passed.

## Verification Observed

- `./.ai/tools/test.sh`: PASS (`23` Python tests, `5` frontend tests)
- `./.ai/tools/lint.sh`: PASS
- `./.ai/tools/security.sh`: PASS
- `./.ai/tools/verify.sh`: PASS, including work-state, docs, setup, format, lint, tests, dependency policy/scans, security, and build

## Notes

- `deployment/docker/scripts/smoke-projects.sh` now retries initial migration connection after `pg_isready`, which is a pragmatic local-startup hardening and does not broaden scope.
- T003 is approved for transition from `verified` to `reviewed`.
