# Task T002: Authentication, user management, initial user, and audit actor foundation

- Status: reviewed
- Parent requirement: support-knowledge-miner-mvp1
- Plan: `.ai/work/support-knowledge-miner-mvp1/PLAN.md`
- Depends on: T001
- Owner/agent: implementer
- Last updated: 2026-07-19

## Objective

Implement simple authentication, equal-permission user management, one-time initial user creation, password hashing, self-delete protection, and audit actor persistence foundation.

## Scope

### In scope

- User persistence with username, first name, last name, email, password hash.
- Established password-hashing algorithm.
- Sign-in/session or equivalent authenticated request mechanism.
- Create/edit/delete users and set/change other users' passwords.
- Self-delete denial.
- Initial user seed through environment/configuration or migration/seed.
- Audit event foundation with acting user identity for protected mutations.
- UI workflows for sign-in and user management, or backend plus minimal UI route if phased.

### Out of scope

- Differentiated roles/permissions.
- Password reset email or external identity providers.
- Project lifecycle behavior except audit integration hooks.

## Preconditions

- T001 complete.
- ADR-0005 accepted.
- Security guidelines apply.

## Affected files or components

- Backend auth/user/audit modules.
- Database migrations.
- Frontend sign-in and user-management screens.
- Tests.

## Acceptance criteria

- [x] Spec AC-11: Users can sign in with username/password.
- [x] Spec AC-12: Initial user can be created once from environment/configuration or migration/seed.
- [x] Spec AC-13: Any authenticated user can create another user, edit another user's username/name/email, and set/change another user's password.
- [x] Spec AC-14: Any authenticated user can delete another user, but cannot delete themselves.
- [x] Spec AC-15: Stored user passwords are password hashes and cannot be retrieved in plaintext through normal read interfaces.
- [x] Spec AC-16: Auditable actions persist the acting user identity.
- [x] Spec AC-30: UI prevents access to protected screens before sign-in.

## Implementation constraints

- Never store or return plaintext passwords.
- Do not invent custom cryptography; use an established password-hashing library.
- Default protected operations to require authenticated identity.
- Add negative tests for invalid credentials and self-delete.

## Applicable specification and test seam

- Specification criteria: AC-11 through AC-16, AC-30.
- Primary observable boundary for this task: backend auth/user APIs and sign-in/user-management UI workflows.
- Implementation-specific boundaries to avoid testing directly: password hash internals beyond verifying plaintext is not stored and verification works.

## Verification

- [x] Focused tests
- [x] Relevant linting and static analysis
- [x] Security or dependency checks when applicable
- [x] Documentation assessment

Exact commands:

```bash
./.ai/tools/test.sh
./.ai/tools/security.sh
./.ai/tools/lint.sh
python .ai/tools/check-docs.py
```

## Risks or blockers

- Security-focused review required.
- New password-hashing/session dependencies require dependency-policy compliance.

## Result

Implemented T002 authentication, user management, sessions, initial seed, audit foundation, and API-backed protected UI:

- Added FastAPI app factory and ASGI entrypoint with `/api/auth/sign-in`, `/api/auth/sign-out`, `/api/auth/me`, and `/api/users` CRUD/password endpoints.
- Added Argon2id password hashing through `argon2-cffi`; stored password hashes are never returned through API response models.
- Added server-side sessions in PostgreSQL; bearer tokens are returned once on sign-in and only SHA-256 token hashes are stored.
- Added one-time initial user seed from `SKM_INITIAL_USERNAME`, `SKM_INITIAL_PASSWORD`, `SKM_INITIAL_EMAIL`, and optional first/last name environment variables.
- Added equal-permission user service supporting create, edit, password set/change, delete-other, and self-delete denial.
- Added audit event persistence with acting user identity for sign-in, sign-out, initial seed, user create/update/password/delete.
- Added migration `0002_auth_users_audit.sql` for `users`, `user_sessions`, and `audit_events`.
- Replaced the starter React page with a minimal T002 sign-in and user-management workflow that calls `/api/auth/sign-in`, only opens protected screens after a successful backend response, loads users through authenticated `/api/users`, sends bearer tokens on user actions, keeps password fields write-only, handles invalid credentials generically, and surfaces backend-unavailable failures.
- Added backend unit/schema tests, FastAPI API-boundary tests, frontend API-backed workflow tests, and `deployment/docker/scripts/smoke-auth-users.sh` for a real local PostgreSQL auth/user/audit smoke.

Dependency additions:

- `fastapi>=0.116,<1`: local backend API framework for authenticated HTTP boundaries. Standard library has no ASGI framework or OpenAPI/request validation support. Locked in `uv.lock`; replaceable behind `backend.api.create_app` if needed.
- `argon2-cffi>=25,<26`: established Argon2id password-hashing implementation. Standard library does not provide password hashing suitable for stored credentials. Locked in `uv.lock`; replaceable behind `backend.auth.passwords` if needed.
- `httpx2>=2.7.0` in the dev group: required by the installed Starlette/FastAPI `TestClient` for API-boundary tests. It is test-only, locked in `uv.lock`, and removable if the project later standardizes on a different ASGI integration-test client.

Verification evidence:

- `deployment/docker/scripts/smoke-auth-users.sh` passed with `auth_users_audit_smoke=ok`; it applied migrations, seeded the initial user once, signed in, authenticated the session, created/updated/password-changed/deleted another user, denied self-delete, verified plaintext password was not stored, verified plaintext session token was not stored, and verified audit rows were persisted.
- `./.ai/tools/test.sh` passed after review remediation: Python `19 passed`; frontend `4 passed`.
- `./.ai/tools/lint.sh` passed: ruff, mypy, oxlint, TypeScript, shellcheck.
- `./.ai/tools/format.sh --check` passed.
- `./.ai/tools/security.sh` passed.
- `./.ai/tools/check-dependencies.sh` passed: dependency policy, `pip-audit`, and `npm audit --audit-level=high`.
- `./.ai/tools/build.sh` passed.
- `./.ai/tools/verify.sh` passed after review remediation, including work-state, documentation, setup, format, lint, tests, dependency policy/scans, security, and build.

Skipped checks: none.

Residual risks:

- The React T002 UI is still a minimal workflow slice; cohesive routing/navigation and broader MVP shell remain in T010 as planned.
- The API uses bearer token sessions suitable for the local MVP. Cookie/CSRF hardening can be revisited if browser-based authenticated API calls become the primary integration path.

Review remediation:

- Addressed P2 frontend auth bypass by replacing local mock sign-in with API-backed sign-in, authenticated user loading, bearer-token user actions, generic invalid-credential handling, and backend-unavailable handling.
- Addressed P2 API-boundary coverage by adding FastAPI `TestClient` tests for successful sign-in, invalid credentials, missing/invalid bearer token rejection, authenticated user list/create/update/password/delete, self-delete denial, and response redaction.
