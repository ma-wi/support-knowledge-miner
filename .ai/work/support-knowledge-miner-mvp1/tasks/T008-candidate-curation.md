# Task T008: Candidate curation foundation and candidate editor

- Status: reviewed
- Parent requirement: support-knowledge-miner-mvp1
- Plan: `.ai/work/support-knowledge-miner-mvp1/PLAN.md`
- Depends on: T007
- Owner/agent: implementer
- Last updated: 2026-07-23

## Objective

Implement support knowledge candidate persistence, manual curation fields, source assignments, statuses/types, and candidate editor UI.

## Scope

### In scope

- Candidate schema for accepted candidate types/statuses.
- Candidate source assignment schema linking to clusters/source records.
- Manual/effective/generated field separation for candidate fields.
- Candidate list/editor UI.
- Status changes and notes.
- Source assignment drilldown.

### Out of scope

- High-quality LLM candidate generation unless already available from earlier analysis seam.
- Export CSV generation.

## Preconditions

- T007 complete.

## Affected files or components

- Backend candidate/curation modules.
- Database migrations.
- Frontend candidate editor.
- Tests.

## Acceptance criteria

- [x] Spec AC-22: Automatic values, manual overrides, and effective values are distinguishable for candidates.
- [x] Spec AC-23: Manual curation remains intact after reopening project and after creating a later analysis run.
- [x] Spec AC-24: Candidate/source traceability reaches original imported source fields.
- [x] Spec AC-29: UI exposes candidate editor workflow.

## Implementation constraints

- Keep generated and manually edited values separate.
- Preserve candidate source assignments for traceability.
- Do not require cloud provider calls in mandatory tests.

## Applicable specification and test seam

- Specification criteria: AC-22, AC-23, AC-24, AC-29.
- Primary observable boundary for this task: candidate/curation API/service and candidate editor UI.
- Implementation-specific boundaries to avoid testing directly: UI component internal state.

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

- Candidate generation quality is not the goal of this task; focus on curation and persistence.
- Review 2026-07-22 returned T008 to `in-progress`: Candidate Editor save serialized untouched generated multi-value fields as empty manual overrides, which could drop effective generated alternatives/dependencies/parameters during unrelated curation edits. Remediation on 2026-07-23 preserves `null` for untouched manual multi-value fields and is verified.
- Re-review 2026-07-23 returned T008 to `in-progress`: the PATCH service cleared omitted existing manual values, and the Candidate Editor did not expose candidate parameters or distinguish generated/manual/effective values for all editable candidate fields. Remediation on 2026-07-23 preserves omitted fields, keeps explicit clear semantics, exposes parameter editing, and is verified.

## Result

- Added candidate and candidate-source persistence in `0008_candidates.sql`, including accepted candidate types/statuses, generated/manual field separation, and project-scoped source assignments.
- Added `CandidateService` with authenticated API routes to create a candidate from a cluster, list project candidates, save manual curation overrides, and drill down to original source `ticketid`, `messagegroupid`, `message`, and `answer`.
- Added Candidate Editor UI for creating candidates from loaded clusters, distinguishing auto/manual/effective values, editing candidate type/status/question/answer/notes, and inspecting source assignments.
- Added regression coverage for migration order/schema, API authentication and response contracts, candidate curation persistence across later analysis runs, and source traceability.
- Documentation assessed: `README.md` and `.ai/PROJECT_CONTEXT.md` need no durable update for this internal T008 implementation because the accepted specification already documents the candidate-curation workflow and no setup/operation contract changed.
- Remediated review P2 by changing the Candidate Editor save payload to preserve `null` for untouched manual alternative questions, parameters, and external dependencies. Existing explicit manual list clears remain representable as empty arrays when a manual override already existed, while generated effective values remain intact for unrelated status/notes edits.
- Added frontend regression coverage asserting an unrelated Candidate save sends `null` for untouched generated multi-value fields instead of empty overrides.
- Added backend service regression coverage asserting a status-only update leaves generated alternatives, parameters, and external dependencies as effective values when no manual override is supplied.
- Remediated re-review P2 by carrying PATCH field-presence from FastAPI `model_fields_set` into `CandidateService`, so omitted fields are preserved while explicit `null` still clears manual overrides.
- Added service and API regression coverage proving partial status/notes updates preserve existing scalar and structured manual curation, and explicit clear requests remove the selected overrides.
- Extended the Candidate Editor to show Auto/Manual/Effective values for question, answer, alternatives, parameters, and external data dependencies, and to edit manual parameters as a JSON object.
- Added frontend coverage for parameterized candidates, including parameter editing and preserving generated parameters/dependencies when no manual override is made.

Verification observed on 2026-07-23:

- `npm test -- --run src/App.test.tsx`: PASS with frontend `8 passed`.
- Direct `pytest tests/candidates/test_candidate_service.py tests/api/test_candidate_api_integration.py` outside the project environment failed during collection because the system Python environment did not have project dependencies/import path; canonical repository test execution below was used instead.
- `uv run --locked python -m pytest tests/candidates/test_candidate_service.py tests/api/test_candidate_api_integration.py`: PASS with Python `9 passed`.
- `./.ai/tools/test.sh`: PASS with Python `58 passed`; frontend `8 passed`.
- `./.ai/tools/format.sh --check`: PASS.
- `./.ai/tools/lint.sh`: PASS.
- `./.ai/tools/security.sh`: PASS.
- `python .ai/tools/check-docs.py`: PASS.
- `python .ai/tools/check-work-state.py`: PASS.
- `./.ai/tools/verify.sh`: PASS, including work-state, documentation, setup, format, lint, tests, dependency policy, security, and build.
