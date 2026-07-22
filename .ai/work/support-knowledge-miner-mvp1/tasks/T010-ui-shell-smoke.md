# Task T010: End-to-end UI shell, shared states, and fixture smoke coverage

- Status: ready
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

- [ ] Spec AC-29: UI exposes required screens or equivalent workflows.
- [ ] Spec AC-30: UI prevents access to protected screens before sign-in.
- [ ] Spec AC-31: Provider settings UI behavior is reachable in shell.
- [ ] Spec AC-32: Import UI summary/log behavior is reachable in shell.
- [ ] Spec AC-33: Run monitor UI state behavior is reachable in shell.
- [ ] Spec AC-34: Cluster explorer UI route/state exists where feature task has implemented data.
- [ ] Spec AC-35: Export UI route/state exists where feature task has implemented data.

## Implementation constraints

- Preserve established app conventions unless intentionally redesigned.
- Avoid exposing secrets in UI errors or logs.
- Use purposeful frontend design, not generic placeholder screens, while respecting MVP scope.

## Applicable specification and test seam

- Specification criteria: AC-29 through AC-35.
- Primary observable boundary for this task: UI routes/workflows and smoke tests.
- Implementation-specific boundaries to avoid testing directly: internal component state and exact CSS layout coordinates.

## Verification

- [ ] Focused tests
- [ ] Relevant linting and static analysis
- [ ] Security or dependency checks when applicable
- [ ] Documentation assessment

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

