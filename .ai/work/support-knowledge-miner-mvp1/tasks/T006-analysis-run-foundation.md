# Task T006: Analysis-run job scaffold, embeddings/vector persistence seam, and run monitor

- Status: ready
- Parent requirement: support-knowledge-miner-mvp1
- Plan: `.ai/work/support-knowledge-miner-mvp1/PLAN.md`
- Depends on: T004, T005
- Owner/agent: implementer
- Last updated: 2026-07-19

## Objective

Implement the analysis-run foundation: background job state, reproducibility metadata, profile snapshots, embedding/vector persistence seam, and run monitor UI.

## Scope

### In scope

- Start/list/read analysis runs for a project.
- Background job scaffold with queued/running/completed/failed states.
- Run metadata: project, dataset version, profile snapshot, provider/model, parameters, timestamps, progress, errors.
- Embedding/vector record schema and persistence seam using PostgreSQL/pgvector where practical.
- Stub/local deterministic analysis path for tests and UI smoke.
- Run monitor UI.

### Out of scope

- Production-grade queue infrastructure.
- Full clustering quality implementation.
- Mandatory live OpenAI or real vLLM inference in tests.

## Preconditions

- T004 and T005 complete.

## Affected files or components

- Backend analysis run/job modules.
- Database migrations.
- Frontend run monitor.
- Tests.

## Acceptance criteria

- [ ] Spec AC-19: Background analysis runs persist status, progress, errors, profile snapshot, dataset version, provider/model, parameters, and timestamps.
- [ ] Spec AC-20: Embeddings/vector records persist with dimensionality, model/profile/run references, and source-object references.
- [ ] Spec AC-28: Local fixture workflows can complete without OpenAI by using vLLM-compatible or stubbed local profile.
- [ ] Spec AC-33: Run monitor UI distinguishes queued/running/completed/failed states and shows required metadata.

## Implementation constraints

- Failed runs must preserve diagnostic state.
- Do not hide partial/failed state as successful.
- Avoid full pairwise all-record vector computation in any scaffold intended for scale.

## Applicable specification and test seam

- Specification criteria: AC-19, AC-20, AC-28, AC-33.
- Primary observable boundary for this task: analysis-run API/service and run monitor UI.
- Implementation-specific boundaries to avoid testing directly: job scheduler internals except through observable state transitions.

## Verification

- [ ] Focused tests
- [ ] Relevant linting and static analysis
- [ ] Security or dependency checks when applicable
- [ ] Documentation assessment

Exact commands:

```bash
./.ai/tools/test.sh
./.ai/tools/lint.sh
python .ai/tools/check-docs.py
```

## Risks or blockers

- Job execution architecture can become broad; keep this task to scaffold and deterministic seam.

## Result

