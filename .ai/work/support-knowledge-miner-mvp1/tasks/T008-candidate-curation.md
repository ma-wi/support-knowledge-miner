# Task T008: Candidate curation foundation and candidate editor

- Status: ready
- Parent requirement: support-knowledge-miner-mvp1
- Plan: `.ai/work/support-knowledge-miner-mvp1/PLAN.md`
- Depends on: T007
- Owner/agent: implementer
- Last updated: 2026-07-19

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

- [ ] Spec AC-22: Automatic values, manual overrides, and effective values are distinguishable for candidates.
- [ ] Spec AC-23: Manual curation remains intact after reopening project and after creating a later analysis run.
- [ ] Spec AC-24: Candidate/source traceability reaches original imported source fields.
- [ ] Spec AC-29: UI exposes candidate editor workflow.

## Implementation constraints

- Keep generated and manually edited values separate.
- Preserve candidate source assignments for traceability.
- Do not require cloud provider calls in mandatory tests.

## Applicable specification and test seam

- Specification criteria: AC-22, AC-23, AC-24, AC-29.
- Primary observable boundary for this task: candidate/curation API/service and candidate editor UI.
- Implementation-specific boundaries to avoid testing directly: UI component internal state.

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

- Candidate generation quality is not the goal of this task; focus on curation and persistence.

## Result

