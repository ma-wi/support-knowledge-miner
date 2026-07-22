# Task T006: Analysis-run job scaffold, embeddings/vector persistence seam, and run monitor

- Status: reviewed
- Parent requirement: support-knowledge-miner-mvp1
- Plan: `.ai/work/support-knowledge-miner-mvp1/PLAN.md`
- Depends on: T004, T005
- Owner/agent: implementer
- Last updated: 2026-07-22

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

- [x] Spec AC-19: Background analysis runs persist status, progress, errors, profile snapshot, dataset version, provider/model, parameters, and timestamps.
- [x] Spec AC-20: Embeddings/vector records persist with dimensionality, model/profile/run references, and source-object references.
- [x] Spec AC-28: Local fixture workflows can complete without OpenAI by using vLLM-compatible or stubbed local profile.
- [x] Spec AC-33: Run monitor UI distinguishes queued/running/completed/failed states and shows required metadata.

## Implementation constraints

- Failed runs must preserve diagnostic state.
- Do not hide partial/failed state as successful.
- Avoid full pairwise all-record vector computation in any scaffold intended for scale.

## Applicable specification and test seam

- Specification criteria: AC-19, AC-20, AC-28, AC-33.
- Primary observable boundary for this task: analysis-run API/service and run monitor UI.
- Implementation-specific boundaries to avoid testing directly: job scheduler internals except through observable state transitions.

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

- Job execution architecture can become broad; keep this task to scaffold and deterministic seam.
- T006 review found that run execution is synchronous in the start request, making queued/running background states unobservable through the API/UI. Remediation must split run creation from execution through an explicit local background-job seam and add tests for observable non-terminal states.

## Result

- Added `analysis_runs` and `embeddings` schema in migration `0006_analysis_runs.sql`, including run status/progress/profile snapshot/provider/model/parameters/diagnostics timestamps and an embedding persistence seam with dimensionality, model/profile/run, dataset, and source-object references.
- Added `backend.analysis.AnalysisService` with authenticated API endpoints to start, list, read, and inspect embedding metadata for project-scoped analysis runs.
- Implemented a deterministic local scaffold path that starts from queued, transitions through running, writes message/answer embedding seam rows without external model calls, and completes with diagnostics; failures preserve failed run state and error metadata.
- Added Run Monitor UI to start runs from imported dataset versions and analysis profiles and to display status, progress, provider/model, dataset version, timestamps, errors, and diagnostics.
- Added service, API, migration, and frontend smoke coverage for run persistence, project-scoped contracts, embedding metadata, and local fixture completion without OpenAI.
- Remediated review P2 by splitting run creation from execution: `start_run()` now persists and returns `queued`, the API enqueues execution through an explicit local background-job seam, and `execute_queued_run()` performs the deterministic scaffold separately. Tests now prove a newly started run is observable before terminal completion and that API list/read responses distinguish `queued`, `running`, `completed`, and `failed` states.
- Removed generated `__pycache__` handoff artifacts under `backend/` and `tests/`.
- Verification observed on 2026-07-22:
  `./.ai/tools/format.sh --check`,
  `./.ai/tools/lint.sh`,
  `./.ai/tools/test.sh`,
  `./.ai/tools/security.sh`,
  `python .ai/tools/check-docs.py`,
  `./.ai/tools/verify.sh`.
