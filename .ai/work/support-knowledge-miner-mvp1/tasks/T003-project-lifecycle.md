# Task T003: Project lifecycle and isolation

- Status: reviewed
- Parent requirement: support-knowledge-miner-mvp1
- Plan: `.ai/work/support-knowledge-miner-mvp1/PLAN.md`
- Depends on: T001, T002
- Owner/agent: implementer
- Last updated: 2026-07-19

## Objective

Implement project create/open/list/rename/delete workflows with strict project isolation and audited mutations.

## Scope

### In scope

- Project schema/API/service.
- Project list/open/create/rename/delete UI workflow.
- Delete confirmation behavior.
- Project-scoped data-access guard pattern for later tasks.
- Tests proving project isolation.

### Out of scope

- Importing records.
- Analysis profiles/runs.
- Candidate/export behavior.

## Preconditions

- T001 and T002 complete.
- ADR-0001 accepted.

## Affected files or components

- Backend project modules.
- Database migrations.
- Frontend project home.
- Tests.

## Acceptance criteria

- [x] Spec AC-1: User can create, open/list, rename, and delete projects through supported interfaces.
- [x] Spec AC-2: Project isolation is enforced.
- [x] Spec AC-16: Auditable actions persist acting user identity for project mutations.
- [x] Spec AC-29: UI exposes project home workflow.

## Implementation constraints

- All project-owned queries must enforce project scope.
- Project deletion is destructive and must require explicit confirmation in UI.
- Do not implement project duplicate/export unless specification changes.

## Applicable specification and test seam

- Specification criteria: AC-1, AC-2, AC-16, AC-29.
- Primary observable boundary for this task: backend project APIs/services and project home UI.
- Implementation-specific boundaries to avoid testing directly: ORM internals.

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

- Missing project scope in later queries is a leakage risk; establish reusable guard patterns now.

## Result

Implemented T003 project lifecycle and project home workflow:

- Added migration `0003_projects.sql` with stable project IDs, names, lifecycle state, timestamps, actor columns, and active-project index.
- Added `ProjectService` for list/open/create/rename/delete with authenticated actor audit events.
- Added FastAPI `/api/projects` and `/api/projects/{project_id}` endpoints for list, create, open, rename, and delete.
- Project delete requires the current project name as confirmation and removes the project row from subsequent open/list responses.
- Extended the authenticated frontend with a project home summary, project list, create/open/rename/delete workflows, empty state, and delete confirmation input.
- Added API-boundary tests for protected project routes and lifecycle behavior.
- Added migration tests and `deployment/docker/scripts/smoke-projects.sh` for a real local PostgreSQL/FastAPI project lifecycle smoke.

Verification evidence:

- Review remediation for the P2 stale-confirmation finding changed project deletion
  to an atomic `DELETE ... WHERE id = %s AND name = %s ... RETURNING name`
  operation and added a regression test that fails if deletion can proceed
  without the confirmed current project name.
- `deployment/docker/scripts/smoke-projects.sh` passed with `project_lifecycle_smoke=ok`; it applied migrations, seeded/sign-in an initial user, created two projects, listed them, opened the exact requested project, renamed one project, rejected delete with mismatched confirmation, deleted with matching confirmation, verified deleted project no longer opens/lists, and verified project audit events.
- `./.ai/tools/test.sh` passed after remediation: Python `23 passed`; frontend `5 passed`.
- `./.ai/tools/format.sh --check` passed.
- `./.ai/tools/lint.sh` passed: ruff, mypy, oxlint, TypeScript, shellcheck.
- `./.ai/tools/security.sh` passed.
- `./.ai/tools/check-dependencies.sh` passed: dependency policy, `pip-audit`, and `npm audit --audit-level=high`.
- `./.ai/tools/build.sh` passed.
- `./.ai/tools/verify.sh` passed after remediation, including work-state, documentation, setup, format, lint, tests, dependency policy/scans, security, and build.

Skipped checks: none.

Residual risks:

- Project deletion currently removes the project row. Later project-owned tables/files introduced by T004+ must add database cascades and artifact deletion as those resources become real.
- The frontend remains a compact MVP workflow surface; T010 will consolidate navigation and shared shell states.
- `deployment/docker/scripts/smoke-projects.sh` now retries the initial migration
  connection briefly because `pg_isready` can report readiness before PostgreSQL
  accepts the first psycopg connection during container startup.
