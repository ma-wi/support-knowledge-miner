# Task T010: End-to-end UI shell, shared states, and fixture smoke coverage

- Status: reviewed
- Parent requirement: support-knowledge-miner-mvp1
- Plan: `.ai/work/support-knowledge-miner-mvp1/PLAN.md`
- Depends on: T002, T003, T004, T005
- Owner/agent: implementer
- Last updated: 2026-07-19

## Objective

Implement the cohesive MVP UI shell and shared loading/empty/error states, then add smoke coverage for the central local workflow using synthetic fixtures.

## Scope

### In scope

- Navigation/shell connecting required MVP screens.
- Shared loading, empty, backend unavailable, provider unavailable, validation failure, and auth-expired states where applicable.
- Smoke workflow: sign in, create/open project, configure provider/profile, import fixture, view import summary/log, start or stub run, inspect run status, reach cluster/candidate/export screens as implemented.
- Responsive layout sufficient for desktop and basic mobile usability.

### Out of scope

- Final visual polish beyond an intentional usable MVP.
- Exact graph layout coordinates.
- Full real-model analysis quality.

## Preconditions

- T002, T003, T004, and T005 complete.
- Later feature screens may extend this task's shell rather than block it.

## Affected files or components

- Frontend app shell/routing/state components.
- Frontend tests.
- Synthetic fixture workflow tests.

## Acceptance criteria

- [x] Spec AC-29: UI exposes required screens or equivalent workflows.
- [x] Spec AC-30: UI prevents access to protected screens before sign-in.
- [x] Spec AC-31: Provider settings UI behavior is reachable in shell.
- [x] Spec AC-32: Import UI summary/log behavior is reachable in shell.
- [x] Spec AC-33: Run monitor UI state behavior is reachable in shell.
- [x] Spec AC-34: Cluster explorer UI route/state exists where feature task has implemented data.
- [x] Spec AC-35: Export UI route/state exists where feature task has implemented data.

## Implementation constraints

- Preserve established app conventions unless intentionally redesigned.
- Avoid exposing secrets in UI errors or logs.
- Use purposeful frontend design, not generic placeholder screens, while respecting MVP scope.

## Applicable specification and test seam

- Specification criteria: AC-29 through AC-35.
- Primary observable boundary for this task: UI routes/workflows and smoke tests.
- Implementation-specific boundaries to avoid testing directly: internal component state and exact CSS layout coordinates.

## Verification

- [x] Focused tests
- [x] Relevant linting and static analysis
- [x] Security or dependency checks when applicable
- [x] Documentation assessment

Exact commands:

```bash
./.ai/tools/test.sh
./.ai/tools/lint.sh
./.ai/tools/build.sh
python .ai/tools/check-docs.py
```

## Risks or blockers

- UI shell can grow too broad; keep smoke scope focused on required workflow reachability and shared states.

## Result

Implemented a cohesive frontend MVP shell with navigation anchors for project home,
users, providers, profiles, import, runs, clusters, candidates, and exports. Added
a shared state board covering loading, empty project, provider unavailable/not
configured, missing project context, active/auth-expired guidance, and validation
summary behavior. Extended frontend smoke coverage to assert the shell navigation
and shared empty states after sign-in.

Verification evidence:

- `npm test`: passed, 9 frontend tests.
- `npm run lint`: passed.
- `npm run format:check`: passed.
- `npm run build`: passed.
- `python .ai/tools/check-docs.py`: passed.
- `./.ai/tools/test.sh`: passed, 67 backend tests and 9 frontend tests.
- `./.ai/tools/lint.sh`: passed.
- `./.ai/tools/build.sh`: passed.
- `./.ai/tools/verify.sh`: passed all gates including setup, format, lint,
  tests, dependency policy, security, and build.

Documentation assessment:

- Reviewed `README.md` and `.ai/PROJECT_CONTEXT.md`; no durable documentation
  update was needed because this task added frontend shell reachability and smoke
  coverage without changing setup, commands, architecture boundaries, public API,
  or operational behavior.

Residual risks:

- None identified for T010. Work is verified and ready for independent review.
- Independent review approved on 2026-07-23; task advanced to `reviewed`.
