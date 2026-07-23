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

---

# Review: support-knowledge-miner-mvp1 T004 import datasets

- Reviewer: Codex
- Date: 2026-07-22
- Scope reviewed: T004 CSV/JSON import, dataset versions, import logs, import UI workflow, migration, fixtures/tests, and local smoke verification. T005-T010 remain `ready` and were not reviewed as implemented behavior.
- Verdict: APPROVE

## Findings

No blocking or material findings found for T004.

## Coverage Reviewed

- AC-3/AC-4: CSV and JSON imports create project-scoped dataset versions and persisted message pairs.
- AC-5: Missing CSV headers, malformed/non-list JSON failures produce failed import logs without dataset versions.
- AC-6: Invalid records are skipped with persisted row/object locations and reasons; duplicate `ticketid` + `messagegroupid` records are accepted.
- AC-7: Zero-valid-record imports fail clearly and create no dataset version.
- AC-32: The authenticated UI shows total/imported/skipped counts, failure reason, dataset version ID, and persisted log detail access.

## Evidence

- `backend/imports/service.py` validates source type, bounds imported content to 5 MiB, parses CSV/JSON, persists import logs/skipped entries, creates dataset versions only when valid records exist, and scopes log/list/detail queries by `project_id`.
- `backend/db/migrations/0004_import_datasets.sql` adds project-scoped `import_logs`, `dataset_versions`, `message_pairs`, and `import_log_entries` tables with constraints and indexes.
- `tests/imports/test_import_service.py`, `tests/api/test_import_api_integration.py`, `frontend/src/App.test.tsx`, and `deployment/docker/scripts/smoke-imports.sh` cover parser, API, UI, migration/smoke seams relevant to T004.

## Verification Observed

- `./.ai/tools/format.sh --check`: PASS
- `./.ai/tools/lint.sh`: PASS
- `./.ai/tools/test.sh`: PASS (`33` Python tests, `6` frontend tests)
- `./.ai/tools/check-dependencies.sh`: PASS, including `pip-audit` and `npm audit --audit-level=high`
- `./.ai/tools/security.sh`: PASS
- `./.ai/tools/build.sh`: PASS
- `./.ai/tools/verify.sh`: PASS, including work-state, docs, setup, format, lint, tests, dependency policy/scans, security, and build
- `bash -x deployment/docker/scripts/smoke-imports.sh`: PASS (`imports_smoke=ok`) after an initial non-diagnostic `deployment/docker/scripts/smoke-imports.sh` run exited with code 1 and no output; traced rerun did not reproduce the failure.

## Notes

- Residual non-blocking risk: concurrent imports into the same project compute `version_number` with `MAX(version_number) + 1`; the unique constraint protects integrity, but a simultaneous import could fail instead of retrying. This is acceptable for the current local MVP slice, but should be hardened before relying on concurrent multi-user imports.
- T004 is approved for transition from `verified` to `reviewed`.

---

# Review: support-knowledge-miner-mvp1 T004/T005 provider-profile implementation

- Reviewer: Codex
- Date: 2026-07-22
- Scope reviewed: T004 regression surface and T005 global provider settings, OpenAI/vLLM configuration, analysis profiles, API/UI behavior, migration, tests, and local smoke verification.
- Verdict: REQUEST_CHANGES

## Findings

### P1: OpenAI API keys are stored as plaintext-readable database values

- Location: `backend/db/migrations/0005_providers_profiles.sql:4`; `backend/providers/service.py:211`
- Evidence: The provider migration creates `provider_configurations.api_key_secret text`, and `ProviderService.upsert_configuration()` writes `clean_api_key` directly into that field. Repository search found no encryption, local secret-store integration, key wrapping, or equivalent protection. The smoke script explicitly queries `api_key_secret` from the database, confirming that normal database read access can retrieve the stored value before removal. API/UI responses are redacted, but storage itself remains plaintext-readable.
- Impact: This violates the accepted security requirement that OpenAI keys must not be stored in plaintext-readable form and the specification statement that API keys may be stored in a local secret mechanism or encrypted database field. A local database dump, admin query, or compromised DB credential would expose the cloud provider credential. Because this is a credential-handling requirement and security control, T005 cannot be approved while this remains.
- Required change: Store OpenAI API keys in a local secret mechanism or encrypt them before database persistence using an established cryptographic library/protocol and a key that is not stored alongside the ciphertext in the same table. Keep normal read APIs/UI write-only. Add tests that fail if the submitted API key is stored verbatim in `provider_configurations` and that still verify set/replace/remove plus no API/UI readback.

## Non-Blocking Notes

- T004 import behavior was spot-checked for regression through tests, full verification, and `deployment/docker/scripts/smoke-imports.sh`; no new T004 findings were found.
- T005 API/UI redaction is implemented for normal read interfaces, and profile creation is project-scoped with explicit OpenAI cloud labeling. The blocking issue is secret-at-rest protection, not response redaction.
- Provider checks are bounded for vLLM via `PROVIDER_CHECK_TIMEOUT_SECONDS`; mandatory tests do not require live OpenAI, which matches the accepted test boundary.

## Verification Observed

- `./.ai/tools/lint.sh`: PASS
- `./.ai/tools/test.sh`: PASS (`38` Python tests, `7` frontend tests)
- `./.ai/tools/security.sh`: PASS
- `./.ai/tools/verify.sh`: PASS, including work-state, docs, setup, format, lint, tests, dependency policy/scans, security, and build
- `deployment/docker/scripts/smoke-imports.sh`: PASS (`imports_smoke=ok`)
- `deployment/docker/scripts/smoke-providers-profiles.sh`: PASS (`providers_profiles_smoke=ok`)

## Status

- T004 remains `reviewed`.
- T005 is returned from `verified` to `in-progress` for remediation of the P1 finding.

---

# Re-review: support-knowledge-miner-mvp1 T004/T005

- Reviewer: Codex
- Date: 2026-07-22
- Scope reviewed: Repeat review of T004 import datasets and T005 provider/profile implementation after the earlier interrupted check. Reviewed durable specification, ADR-0002/0003/0004, active plan/task files, current diff, backend API/service code, migrations, frontend workflow/tests, local smoke scripts, security guidance, and full verification.
- Verdict: REQUEST_CHANGES

## Findings

### P1: OpenAI API keys are still stored as plaintext-readable database values

- Location: `backend/db/migrations/0005_providers_profiles.sql:4`; `backend/providers/service.py:211`
- Evidence: The provider migration still defines `provider_configurations.api_key_secret text`. `ProviderService.upsert_configuration()` still passes `clean_api_key` directly into that column on insert/update. No encryption, external local secret store, key wrapping, or equivalent protection exists in the current dependency/configuration surface. API/UI responses redact the key, but database reads can recover the stored credential while configured.
- Impact: This violates the accepted T005/security requirement that OpenAI API keys must not be stored in plaintext-readable form and the specification allowance that keys may be stored in a local secret mechanism or encrypted database field. A local database dump, broad DB read privilege, or compromised database credential would expose the cloud provider credential. Because this is credential handling, T005 cannot be approved.
- Required change: Store OpenAI API keys in a local secret mechanism or encrypt them before database persistence using an established cryptographic library/protocol and a key not stored alongside the ciphertext in the same table. Preserve write-only API/UI behavior. Add regression coverage that fails if the submitted API key is stored verbatim in `provider_configurations`, while still verifying set/replace/remove and no normal API/UI readback.

## T004 Result

No blocking or material findings were found for T004 in this repeat review. Import parser/service/API/UI behavior remains covered for valid CSV/JSON imports, file-level failures, invalid-record skip logs, zero-valid-record failure behavior, duplicate identifiers, project-scoped log/detail access, and UI count/log visibility.

## T005 Notes

- API and UI responses do not expose the OpenAI key through normal read interfaces.
- Project-scoped analysis profiles select configured provider/model pairs and mark OpenAI as cloud usage.
- Provider checks are bounded by `PROVIDER_CHECK_TIMEOUT_SECONDS`; mandatory tests do not require live OpenAI calls.
- These positives do not remediate the secret-at-rest violation above.

## Verification Observed

- `./.ai/tools/lint.sh`: PASS
- `./.ai/tools/test.sh`: PASS (`38` Python tests, `7` frontend tests)
- `./.ai/tools/security.sh`: PASS
- `deployment/docker/scripts/smoke-imports.sh`: PASS (`imports_smoke=ok`)
- `deployment/docker/scripts/smoke-providers-profiles.sh`: PASS (`providers_profiles_smoke=ok`)
- `./.ai/tools/verify.sh`: PASS, including work-state, documentation, setup, format, lint, tests, dependency policy/scans, security, and build

## Status

- T004 remains `reviewed`.
- T005 remains `in-progress` / not approvable until the P1 secret-at-rest finding is remediated and re-reviewed.

---

# Re-review: support-knowledge-miner-mvp1 T005

- Reviewer: Codex
- Date: 2026-07-22
- Scope reviewed: T005 global provider settings, OpenAI/vLLM configuration, analysis profiles, provider credential storage remediation, API/UI redaction behavior, migration/tests, dependency/security policy impact for `cryptography`, local provider/profile smoke script, maintained documentation touched by the current diff, and full verification.
- Verdict: REQUEST_CHANGES

## Findings

### P2: README contains copied agent prompts instead of maintained project documentation

- Location: `README.md:41`
- Evidence: The current README diff appends a `# Prompts` section containing prior German agent instructions such as "Lese zuerst die AGENTS.md..." and review/planning prompts. This is chat/workflow transcript material, not stable project setup, behavior, configuration, architecture, or support documentation.
- Impact: This violates the repository documentation rule to document current truth, durable rationale, and actionable next steps, not chats, tool logs, or work diaries. The README is also included in the Python build artifact observed during `./.ai/tools/verify.sh`, so this transient review/planning text would ship with the package metadata/source distribution if accepted.
- Required change: Remove the prompt transcript section from `README.md` or replace it with durable project documentation relevant to T005/configuration. Keep prompts and temporary review instructions out of maintained docs.

## Remediation Verification

- The prior P1 secret-at-rest finding is remediated for newly saved OpenAI API keys. `ProviderService.upsert_configuration()` now calls `encrypt_provider_secret()` before writing `provider_configurations.api_key_secret`, storage requires `SKM_PROVIDER_ENCRYPTION_KEY`, and regression coverage asserts the submitted key is not stored verbatim.
- Normal provider read/write API responses still expose only `api_key_set`, not the submitted API key.
- The T005 smoke script now verifies that stored OpenAI credentials differ from the submitted value, carry the `fernet:` envelope prefix, and are removed from storage when requested.

## Verification Observed

- `./.ai/tools/format.sh --check`: PASS
- `./.ai/tools/lint.sh`: PASS
- `./.ai/tools/test.sh`: PASS (`40` Python tests, `7` frontend tests)
- `./.ai/tools/check-dependencies.sh`: PASS, including dependency policy, `pip-audit`, and `npm audit --audit-level=high`
- `./.ai/tools/security.sh`: PASS
- `python .ai/tools/check-docs.py`: PASS
- `deployment/docker/scripts/smoke-providers-profiles.sh`: PASS (`providers_profiles_smoke=ok`)
- `./.ai/tools/verify.sh`: PASS, including work-state, documentation, setup, format, lint, tests, dependency policy/scans, security, and build

## Status

- T005 is returned from `verified` to `in-progress` for remediation of the P2 documentation finding.
- After the README prompt transcript is removed or replaced with durable documentation, T005 can be re-reviewed; no remaining blocking provider/profile behavior issue was found in this pass.

---

# Review: support-knowledge-miner-mvp1 T005/T006

- Reviewer: Codex
- Date: 2026-07-22
- Scope reviewed: Combined review of T005 provider/profile implementation and T006 analysis-run foundation after T005 credential/documentation remediation. Reviewed AGENTS.md, CODE_REVIEWER role, project/workflow policy, security/dependency policy surfaces, durable requirement/specification, active plan/task files, provider/profile and analysis-run backend services, API routes, migrations, frontend workflows/tests, dependency changes, maintained documentation, and verification evidence.
- Verdict: REQUEST_CHANGES

## Findings

### P2: Analysis runs are completed synchronously inside the start request, so queued/running background states are not observable

- Location: `backend/analysis/service.py:207`; `backend/api/app.py:653`; `tests/analysis/test_analysis_service.py:183`
- Evidence: `AnalysisService.start_run()` inserts the run as `queued`, then immediately calls `_execute_deterministic_scaffold(run_id)` before returning the POST response. `_execute_deterministic_scaffold()` transitions the row to `running` and then `completed` in the same request path. The API route returns only after `start_run()` completes, and the service test asserts the returned status is already `completed`. No background task, queue worker, scheduler seam, or observable pending/running handoff exists in the current code.
- Impact: This does not satisfy the accepted T006 behavior that analysis jobs run as background jobs with observable status/progress/failure state, and it weakens AC-19/AC-33 because the run monitor cannot observe the required `queued`/`running` lifecycle for normal started runs. A longer future scaffold would also block the request thread instead of returning promptly with a persisted job state.
- Required change: Split run creation from execution. The start endpoint should persist and return a queued or running run promptly, then execute the deterministic scaffold through an explicit background-job seam suitable for local MVP use. Add service/API tests that prove a newly started run is observable before terminal completion and that list/read endpoints can distinguish queued/running/completed/failed states. Keep failed-run diagnostics persisted.

## Non-Blocking Notes

- T005 credential-at-rest remediation is acceptable in this pass: newly saved OpenAI API keys are encrypted with Fernet before database storage, storing credentials requires `SKM_PROVIDER_ENCRYPTION_KEY`, normal provider API/UI responses remain write-only, and regression/smoke coverage checks non-verbatim storage plus removal.
- The new direct dependency `cryptography>=48,<49` is justified in the T005 task file for authenticated credential encryption, is locked to `48.0.1` in `uv.lock`, and passed dependency/security gates. No remaining dependency blocker was found.
- Untracked `__pycache__` files are present under `backend/` and `tests/`; remove them before commit/review handoff hygiene. They are not the cause of this `REQUEST_CHANGES` verdict.

## Verification Observed

- `./.ai/tools/test.sh`: PASS (`44` Python tests, `7` frontend tests)
- `./.ai/tools/lint.sh`: PASS
- `./.ai/tools/security.sh`: PASS
- `./.ai/tools/check-dependencies.sh`: PASS, including `pip-audit` and `npm audit --audit-level=high`
- `python .ai/tools/check-docs.py`: PASS
- `./.ai/tools/verify.sh`: PASS, including work-state, documentation, setup, format, lint, tests, dependency policy/scans, security, and build

## Status

- T005 is approved for transition from `verified` to `reviewed`.
- T006 is returned from `verified` to `in-progress` for remediation of the P2 background-job observability finding.

---

# Re-review: support-knowledge-miner-mvp1 T006

- Reviewer: Codex
- Date: 2026-07-22
- Scope reviewed: T006 remediation for the prior P2 background-job observability finding, including analysis service execution seam, API enqueue behavior, service/API tests, run monitor surface, work-state consistency, security/dependency surfaces, and full verification. T005 remains reviewed from the prior pass.
- Verdict: APPROVE

## Findings

No blocking or material findings remain for T006.

## Prior Finding Rechecked

### P2: Analysis runs are completed synchronously inside the start request, so queued/running background states are not observable

- Previous status: REQUEST_CHANGES
- Current status: resolved
- Evidence: `AnalysisService.start_run()` now persists and returns a `queued` run without executing the deterministic scaffold. The API route calls `analysis_service.enqueue_run(run.id)` after creating the run, and `execute_queued_run()` performs the queued-to-running-to-terminal transition separately. Service tests verify `start_run()` returns `queued` before embeddings are written, then explicit execution completes the run. API tests verify the start response is `queued`, enqueue is called, and list/read contracts distinguish `queued`, `running`, `completed`, and `failed` states with failed-run error metadata.

## Verification Observed

- `./.ai/tools/test.sh`: PASS (`44` Python tests, `7` frontend tests)
- `./.ai/tools/lint.sh`: PASS
- `./.ai/tools/security.sh`: PASS
- `./.ai/tools/check-dependencies.sh`: PASS, including `pip-audit` and `npm audit --audit-level=high`
- `python .ai/tools/check-work-state.py`: PASS
- `python .ai/tools/check-docs.py`: PASS
- `./.ai/tools/verify.sh`: PASS, including work-state, documentation, setup, format, lint, tests, dependency policy/scans, security, and build

## Notes

- The local background runner is intentionally minimal for the MVP scaffold. It is acceptable for T006 because the persistent run state is now observable and execution is isolated behind an explicit seam, but later production-grade queue semantics remain out of scope for this task.
- T006 is approved for transition from `verified` to `reviewed`.

---

# Review: support-knowledge-miner-mvp1 T007

- Reviewer: Codex
- Date: 2026-07-22
- Scope reviewed: T007 clustering foundation, cluster persistence, non-quadratic deterministic scaffold, outlier/unassigned representation, automatic/manual/effective cluster values, cluster API, cluster explorer UI, source traceability, migration/tests, work-state consistency, security/dependency surfaces, and full verification.
- Verdict: APPROVE

## Findings

No blocking or material findings were found for T007.

## Acceptance Criteria Trace

- AC-21: `ClusterService.generate_for_run()` groups message pairs in a single pass using a deterministic prefix scaffold and records `metadata.non_quadratic`; singleton groups are marked `outlier`.
- AC-22: Cluster records persist automatic fields separately from manual overrides, and service/API responses derive effective values without overwriting automatic values.
- AC-24: Cluster memberships link clusters to original `message_pairs`, and source drilldown returns original `ticketid`, `messagegroupid`, `message`, and `answer`.
- AC-34: The UI exposes Cluster Explorer actions, shows Auto/Manual/Effective values distinctly, marks outliers, supports manual override updates, and drills down to source records.

## Verification Observed

- `./.ai/tools/test.sh`: PASS (`48` Python tests, `7` frontend tests)
- `./.ai/tools/lint.sh`: PASS
- `./.ai/tools/security.sh`: PASS
- `./.ai/tools/check-dependencies.sh`: PASS, including `pip-audit` and `npm audit --audit-level=high`
- `python .ai/tools/check-work-state.py`: PASS
- `python .ai/tools/check-docs.py`: PASS
- `./.ai/tools/verify.sh`: PASS, including work-state, documentation, setup, format, lint, tests, dependency policy/scans, security, and build

## Notes

- The clustering quality is intentionally a deterministic scaffold, not a final semantic clustering algorithm. That is acceptable for T007 because the accepted scope requires the persistence/traceability/UI seam and prohibits full pairwise all-record computation, while final tuning remains out of scope.
- T007 is approved for transition from `verified` to `reviewed`.

---

# Review: support-knowledge-miner-mvp1 T008

- Reviewer: Codex
- Date: 2026-07-22
- Scope reviewed: T008 candidate persistence and curation foundation, candidate/source assignment traceability, candidate API, Candidate Editor UI, migration/tests, work-state consistency, security/dependency surfaces, and full verification.
- Verdict: REQUEST_CHANGES

## Findings

### P2: Candidate Editor silently converts untouched generated multi-value fields into empty manual overrides

- Location: `frontend/src/App.tsx:1232`, `frontend/src/App.tsx:1256`, `frontend/src/App.tsx:1259`, `frontend/src/App.tsx:1260`, `frontend/src/App.tsx:1911`, `frontend/src/App.tsx:1920`, `backend/candidates/service.py:201`, `backend/candidates/service.py:208`, `backend/candidates/service.py:215`
- Evidence: the editor renders manual alternative questions and external data dependencies from `candidate.manual... ?? ""`, so a candidate with generated alternatives/dependencies but no manual override shows blank manual fields. On any save, `updateCandidate()` always serializes `manual_alternative_questions` from that blank textarea as `[]`, always serializes `manual_parameters` as `{}`, and serializes `manual_external_data_dependencies` as `[]`. The backend treats every non-NULL manual list/object as an intentional manual value and selects it for the effective value.
- Impact: saving an unrelated edit such as status, title, or notes changes candidate curation state by replacing generated effective alternatives/dependencies/parameters with empty manual overrides. That breaks the T008 requirement to keep generated/manual/effective candidate values meaningfully separate, and it risks dropping generated candidate evidence from later curation/export flows without an explicit curator action.
- Required change: preserve the distinction between "no manual override", "explicitly cleared manual override", and "manual override value". For example, the UI can omit these fields or send `null` when no manual override is intended, and the API/service should have regression coverage for a candidate with generated alternatives/dependencies/parameters where saving only status/notes leaves the effective generated values intact unless the user explicitly clears them.

## Acceptance Criteria Trace

- AC-22: Not satisfied because untouched generated multi-value candidate fields can be replaced by empty manual overrides during a normal editor save.
- AC-23: Not satisfied for the same curation-state preservation path; manual/generated state can be mutated unintentionally before reopening or later-run checks observe it.
- AC-24: Source traceability to original imported fields is implemented and covered.
- AC-29: Candidate Editor workflow is present, but its save behavior needs the P2 remediation above.

## Verification Observed

- `./.ai/tools/test.sh`: PASS (`54` Python tests, `7` frontend tests)
- `./.ai/tools/lint.sh`: PASS
- `./.ai/tools/security.sh`: PASS
- `./.ai/tools/check-dependencies.sh`: PASS, including `pip-audit` and `npm audit --audit-level=high`
- `python .ai/tools/check-work-state.py`: PASS
- `python .ai/tools/check-docs.py`: PASS
- `./.ai/tools/verify.sh`: PASS, including work-state, documentation, setup, format, lint, tests, dependency policy/scans, security, and build

## Status

- T008 is returned from `verified` to `in-progress` for remediation of the P2 Candidate Editor override finding.

---

# Re-review: support-knowledge-miner-mvp1 T008

- Reviewer: Codex
- Date: 2026-07-23
- Scope reviewed: T008 remediation for the prior P2 multi-value override finding, plus the candidate service/API, Candidate Editor UI, migration/tests, accepted criteria, work-state consistency, security/dependency surfaces, and focused/full verification.
- Verdict: REQUEST_CHANGES

## Findings

### P2: Partial candidate updates erase existing manual curation

- Location: `backend/api/app.py:987`; `backend/api/app.py:994`; `backend/candidates/service.py:447`; `backend/candidates/service.py:465`; `tests/candidates/test_candidate_service.py:336`
- Evidence: `CandidateUpdateRequest` defaults every omitted field to `None`, the route copies all of those values into `CandidateManualUpdate`, and `CandidateService.update_candidate()` writes every manual column directly. It does not distinguish an omitted PATCH field from an explicit `null` used to clear an override. Reviewer reproduction first stored `manual_title='Curated title'` and `manual_parameters={'account_id': 'required'}`, then sent a notes-only service update; both existing manual values became `None`. The new status-only regression starts from a candidate with no manual multi-value overrides, so it cannot detect this data loss.
- Impact: API clients performing a normal partial update can silently remove unrelated reviewed curation. This contradicts PATCH semantics, the task's primary API/service seam, and AC-23's durability requirement.
- Required change: preserve omitted fields while retaining an explicit way to clear an override. Carry field-presence information from the request boundary into the service/update query, and add API/service regression coverage that starts with existing scalar and structured manual values, patches only status or notes, and proves all unrelated manual/effective values remain intact. Also cover explicit clearing separately.

### P2: Candidate Editor omits parameters and does not distinguish all generated/manual/effective fields

- Location: `frontend/src/App.tsx:1820`; `frontend/src/App.tsx:1834`; `frontend/src/App.tsx:1919`; `frontend/src/App.tsx:1928`; `docs/specifications/support-knowledge-miner-mvp1.md:264`
- Evidence: the Candidate Editor displays Auto/Manual/Effective only for title/category/status. Question, answer, and alternative questions show only effective values plus an unlabeled manual editor; dependencies have only a manual textarea; candidate parameters have no display or input at all. Nevertheless the API model carries `auto_parameters`, `manual_parameters`, and `effective_parameters`, and UI-09 explicitly requires parameters and external dependencies where applicable plus distinguishable generated/manual values.
- Impact: a curator cannot inspect or edit parameter metadata and cannot reliably tell whether several visible values are generated or manually overridden. AC-22 and the accepted UI-09 portion of AC-29 are therefore incomplete.
- Required change: expose parameters and external dependencies in the Candidate Editor and visibly distinguish automatic, manual, and effective values for the curated candidate fields. Add component coverage for a parameterized candidate, including editing/saving parameters and retaining generated values when no override is made.

## Prior Finding Rechecked

### P2: Candidate Editor silently converts untouched generated multi-value fields into empty manual overrides

- Previous status: REQUEST_CHANGES
- Current status: resolved for the originally reported UI path
- Evidence: the editor now sends `null` for untouched generated alternative questions, parameters, and external dependencies, while an existing manual list can still be cleared to an empty list. The frontend regression asserts the null payload, and the service regression confirms generated effective multi-value fields survive when no manual override exists.

## Verification Observed

- `./.ai/tools/test.sh`: PASS (`55` Python tests, `8` frontend tests)
- `./.ai/tools/lint.sh`: PASS
- `./.ai/tools/security.sh`: PASS
- `./.ai/tools/check-dependencies.sh`: PASS, including `pip-audit` and `npm audit --audit-level=high`
- `python .ai/tools/check-work-state.py`: PASS before the review status transition
- `python .ai/tools/check-docs.py`: PASS before the review status transition
- `./.ai/tools/verify.sh`: PASS, including work-state, documentation, setup, format, lint, tests, dependency policy/scans, security, and build
- Reviewer reproduction of notes-only update after existing manual curation: FAIL as expected; `manual_title` and `manual_parameters` changed from populated values to `None`.

## Status

- T008 is returned from `verified` to `in-progress` for remediation of both P2 findings.

---

# Re-review: support-knowledge-miner-mvp1 T008 remediation

- Reviewer: Codex
- Date: 2026-07-23
- Scope reviewed: T008 remediation for PATCH field-presence handling, candidate multi-value override preservation, Candidate Editor parameter/dependency visibility, candidate service/API contracts, UI regression coverage, work-state consistency, security/dependency surfaces, and full verification.
- Verdict: APPROVE

## Findings

No blocking or material findings were found.

## Prior Findings Rechecked

### P2: Partial candidate updates erase existing manual curation

- Previous status: REQUEST_CHANGES
- Current status: resolved
- Evidence: `CandidateUpdateRequest.model_fields_set` is now passed into `CandidateManualUpdate.fields_to_update`, and `CandidateService.update_candidate()` updates only fields explicitly present in that set. Service and API regressions cover status-only/manual-status-only PATCH requests preserving existing scalar and structured manual values, plus explicit null clearing for selected overrides.

### P2: Candidate Editor omits parameters and does not distinguish all generated/manual/effective fields

- Previous status: REQUEST_CHANGES
- Current status: resolved
- Evidence: The Candidate Editor now renders Auto/Manual/Effective values for question, answer, alternative questions, parameters, and external data dependencies. It exposes `Parameter JSON` editing and keeps generated multi-value values intact when no manual override exists. Frontend coverage asserts parameter editing and generated parameter/dependency preservation.

### P2: Candidate Editor silently converts untouched generated multi-value fields into empty manual overrides

- Previous status: resolved in the prior re-review for the originally reported UI path
- Current status: still resolved
- Evidence: The UI keeps `null` for untouched generated alternative questions, parameters, and external data dependencies; existing manual list/object clears remain explicit as empty arrays/objects.

## Acceptance Criteria Trace

- AC-22: Satisfied for candidates. Automatic, manual, and effective candidate values are persisted separately, exposed by the API, and visibly distinguished in the Candidate Editor.
- AC-23: Satisfied for T008 scope. Manual curation persists through service/API reads and is preserved by later analysis-run creation and unrelated PATCH updates.
- AC-24: Satisfied. Candidate source assignments link back to original imported `ticketid`, `messagegroupid`, `message`, and `answer`, with service/API/UI coverage.
- AC-29: Satisfied for the Candidate Editor workflow implemented in T008.

## Verification Observed

- `./.ai/tools/test.sh`: PASS with Python `58 passed`; frontend `8 passed`.
- `./.ai/tools/lint.sh`: PASS.
- `python .ai/tools/check-docs.py`: PASS.
- `python .ai/tools/check-work-state.py`: PASS before the review status transition.
- `./.ai/tools/verify.sh`: PASS, including work-state, documentation, setup, format, lint, tests, dependency policy/scans, security, and build.

## Notes

- Ignored Python bytecode/cache files exist in the local worktree under generated cache directories. They are covered by `.gitignore` and are not a T008 approval blocker.

## Status

- T008 is approved for transition from `verified` to `reviewed`.

---

# Review: support-knowledge-miner-mvp1 T009

- Reviewer: Codex
- Date: 2026-07-23
- Scope reviewed: T009 candidate CSV export, source-assignment CSV export, export metadata persistence, export API/UI, original-text warnings, migration/tests, work-state consistency, security/privacy surfaces, and full verification.
- Verdict: REQUEST_CHANGES

## Findings

### P2: Candidate exports can contain original source text while metadata and warning say they do not

- Location: `backend/exports/service.py:141`; `backend/exports/service.py:157`; `backend/exports/service.py:170`; `backend/exports/service.py:293`; `backend/exports/service.py:294`; `backend/exports/service.py:295`; `backend/exports/service.py:315`; `backend/candidates/service.py:311`; `backend/candidates/service.py:314`; `backend/candidates/service.py:371`; `backend/candidates/service.py:372`; `frontend/src/App.tsx:1699`
- Evidence: Candidate creation from a cluster stores the first source pair's original `mp.message` and `mp.answer` as `auto_canonical_question` and `auto_canonical_answer`. Candidate CSV export always writes `effective_canonical_question` and `effective_canonical_answer` to the CSV, regardless of `include_original_text`. The same request flag is stored directly as `export_logs.include_original_text`, returned as `contains_original_text`, and controls whether a warning is returned. In the UI the candidate checkbox only says original text should be "marked"; if the user leaves it unchecked, a cluster-derived candidate CSV can still contain source text but the export metadata says `include_original_text=false` and no warning is shown.
- Impact: AC-27 and AC-35 are not satisfied for candidate exports. The export history and CSV `contains_original_text` field can falsely record that original/potentially identifying text was not included, which breaks the accepted privacy requirement and makes later export review/audit unreliable.
- Required change: Make candidate export original-text semantics conservative and testable. Either suppress/redact candidate text fields when `include_original_text=false`, or treat candidate CSV rows that contain cluster-derived/source-derived canonical text as original-text exports by forcing/storing `include_original_text=true`, returning a warning, and writing `contains_original_text=true`. Add service/API/UI regression coverage for a candidate export requested with the checkbox unset where the candidate canonical question/answer originate from source text.

## Acceptance Criteria Trace

- AC-25: Candidate CSV headers match the accepted baseline columns.
- AC-26: Source-assignment CSV headers match the accepted baseline columns, and source `customer_message`/`support_answer` are blank unless original text is requested.
- AC-27: Not satisfied for candidate exports because persisted `include_original_text` can be false even when exported canonical candidate fields contain original source text.
- AC-35: Not satisfied for the same candidate-export path because the UI/API can complete without an original-text warning while original/potentially identifying candidate text is present.

## Verification Observed

- `./.ai/tools/test.sh`: PASS with Python `65 passed`; frontend `8 passed`.
- `./.ai/tools/lint.sh`: PASS.
- `python .ai/tools/check-docs.py`: PASS.
- `python .ai/tools/check-work-state.py`: PASS before the review status transition.
- `./.ai/tools/verify.sh`: PASS, including work-state, documentation, setup, format, lint, tests, dependency policy/scans, security, and build.

## Notes

- The passing tests cover exact headers, source-assignment redaction, export metadata creation, authentication, and UI history. They do not cover the candidate-export false-negative original-text metadata case above.

## Status

- T009 is returned from `verified` to `in-progress` for remediation of the P2 candidate-export original-text metadata/warning finding.

---

# Re-review: support-knowledge-miner-mvp1 T009

- Reviewer: Codex
- Date: 2026-07-23
- Scope reviewed: remediation for candidate export original-text metadata/warning semantics, export service/API/UI behavior, regression tests, task/work-state consistency, and full verification.
- Verdict: APPROVE

## Findings

- No P0/P1/P2/P3 findings.

## Remediation Trace

### P2: Candidate exports can contain original source text while metadata and warning say they do not

- Previous status: REQUEST_CHANGES
- Current status: resolved
- Evidence: `ExportService.export_candidates()` now derives `actual_include_original_text` from the request flag or from cluster/source-derived candidates, writes that value into CSV `contains_original_text`, persists it in `export_logs.include_original_text`, and returns the warning based on the actual value. The API returns the persisted log value rather than echoing the request. The UI stores and displays the returned metadata in export history and shows the warning returned by the backend.

## Acceptance Criteria Trace

- AC-25: Satisfied. Candidate CSV header order is covered by `tests/exports/test_export_service.py` against `CANDIDATE_CSV_COLUMNS`.
- AC-26: Satisfied. Source-assignment CSV header order and original-text redaction behavior are covered by `tests/exports/test_export_service.py`.
- AC-27: Satisfied. Export metadata is persisted with actual original-text inclusion, including a regression where a candidate export requested with `include_original_text=false` is persisted as `true` when candidate text is source-derived.
- AC-35: Satisfied for T009 scope. The frontend exposes export actions/history and displays backend warnings/history for original-text exports, including the conservative candidate-export path.

## Verification Observed

- `./.ai/tools/verify.sh`: PASS. Observed gates: work-state, documentation, setup, format, lint/static analysis, tests, dependency policy/scans, security, and build.
- Python tests: `67 passed`.
- Frontend tests: `8 passed`.

## Notes

- Review did not access production resources.
- `prompts.txt` is listed in `.aiignore`; it was not used as review evidence.

## Status

- T009 is approved for transition from `verified` to `reviewed`.

---

# Review: support-knowledge-miner-mvp1 T010

- Reviewer: Codex
- Date: 2026-07-23
- Scope reviewed: T010 MVP UI shell/navigation, shared loading/empty/backend/provider/auth/validation states, protected-screen gating, local fixture smoke reachability, frontend tests, work-state consistency, and full verification.
- Verdict: APPROVE

## Findings

- No P0/P1/P2/P3 findings.

## Acceptance Criteria Trace

- AC-29: Satisfied. The authenticated shell exposes sign-in, user management, provider settings, project home, profiles, import, run monitor, cluster explorer, candidate editor, and export workflows through navigation and rendered workflow sections.
- AC-30: Satisfied. The protected shell is not rendered before successful API sign-in, and tests cover rejected credentials and backend-unavailable sign-in failures.
- AC-31: Satisfied. Provider settings are reachable from the shell; OpenAI key replacement/removal remains write-only in UI responses, and vLLM endpoint/model configuration is covered.
- AC-32: Satisfied. Import UI displays total/imported/skipped counts, dataset version, failure/validation details, and persisted import-log drilldown.
- AC-33: Satisfied. Run monitor displays status/progress, provider/model, dataset version, timestamps, diagnostics, and errors.
- AC-34: Satisfied. Cluster explorer displays automatic/manual/effective values and supports source-record drilldown.
- AC-35: Satisfied. Export UI displays original-text warnings, export metadata/history, and last CSV output.

## Verification Observed

- `./.ai/tools/verify.sh`: PASS. Observed gates: work-state, documentation, setup, format, lint/static analysis, tests, dependency policy/scans, security, and build.
- Python tests: `67 passed`.
- Frontend tests: `9 passed`.

## Notes

- Review did not access production resources.
- `prompts.txt` is listed in `.aiignore`; it was not used as review evidence.

## Status

- T010 is approved for transition from `verified` to `reviewed`.
