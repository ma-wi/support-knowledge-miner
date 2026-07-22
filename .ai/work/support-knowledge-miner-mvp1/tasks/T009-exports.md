# Task T009: Candidate/source CSV export and export history

- Status: ready
- Parent requirement: support-knowledge-miner-mvp1
- Plan: `.ai/work/support-knowledge-miner-mvp1/PLAN.md`
- Depends on: T008
- Owner/agent: implementer
- Last updated: 2026-07-19

## Objective

Implement candidate and source-assignment CSV exports using accepted baseline columns, export metadata persistence, and export UI warnings for original/potentially identifying text.

## Scope

### In scope

- Candidate CSV export with accepted baseline columns.
- Source-assignment CSV export with accepted baseline columns.
- Export metadata persistence in project database.
- Export history UI.
- Warning/toggle behavior for exports including original text where applicable.
- Tests for exact CSV headers and traceability fields.

### Out of scope

- Optional cluster/audit exports unless already trivial and explicitly scoped.
- Project archive export/import.

## Preconditions

- T008 complete.

## Affected files or components

- Backend export modules.
- Database migrations if needed.
- Frontend export screen/history.
- Tests.

## Acceptance criteria

- [ ] Spec AC-25: Candidate CSV export exactly includes accepted baseline columns.
- [ ] Spec AC-26: Source-assignment CSV export exactly includes accepted baseline columns.
- [ ] Spec AC-27: Export metadata is persisted and records whether original text was included.
- [ ] Spec AC-35: Export UI warns when original/potentially identifying text is included and records export metadata.

## Implementation constraints

- CSV output must be deterministic enough for tests.
- Escape CSV fields correctly.
- Avoid leaking secrets or unrelated project data.

## Applicable specification and test seam

- Specification criteria: AC-25, AC-26, AC-27, AC-35.
- Primary observable boundary for this task: export API/service and export UI.
- Implementation-specific boundaries to avoid testing directly: CSV writer internals beyond output contract.

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

- Exports may include original text; UI warning and metadata must be reliable.

## Result

