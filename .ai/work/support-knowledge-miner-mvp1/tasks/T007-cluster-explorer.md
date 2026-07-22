# Task T007: Clustering foundation, cluster explorer, and source traceability

- Status: ready
- Parent requirement: support-knowledge-miner-mvp1
- Plan: `.ai/work/support-knowledge-miner-mvp1/PLAN.md`
- Depends on: T006
- Owner/agent: implementer
- Last updated: 2026-07-19

## Objective

Implement the first clustering foundation with source traceability, outlier/unassigned handling, and cluster explorer UI.

## Scope

### In scope

- Cluster persistence linked to project, run, dataset/source records.
- Non-quadratic clustering/vector-neighbor path or deterministic placeholder that preserves the non-quadratic architecture seam.
- Outlier/unassigned record representation.
- Automatic/manual/effective value model for cluster fields.
- Cluster explorer UI list/detail/source drilldown.
- Tests for traceability and automatic/manual/effective separation.

### Out of scope

- Advanced graph visualization if not needed for first milestone.
- Final clustering-quality tuning.
- Candidate editor/export.

## Preconditions

- T006 complete.

## Affected files or components

- Backend clustering/cluster modules.
- Database migrations.
- Frontend cluster explorer.
- Tests and fixtures.

## Acceptance criteria

- [ ] Spec AC-21: Clustering implementation avoids full pairwise all-record distance computation and exposes outliers/unassigned records.
- [ ] Spec AC-22: Automatic values, manual overrides, and effective values are distinguishable for clusters.
- [ ] Spec AC-24: Candidate/source traceability groundwork reaches original imported source fields for clusters.
- [ ] Spec AC-34: Cluster explorer UI distinguishes automatic/manual/effective values and provides source drilldown.

## Implementation constraints

- Preserve source traceability on all cluster memberships.
- Do not overwrite manual values with later run output.
- Avoid tests that assert exact cluster quality on non-reference real data.

## Applicable specification and test seam

- Specification criteria: AC-21, AC-22, AC-24, AC-34.
- Primary observable boundary for this task: cluster API/service and cluster explorer UI.
- Implementation-specific boundaries to avoid testing directly: exact internal vector index implementation.

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

- Clustering algorithm choice may need later tuning; keep architecture replaceable and profile-driven.

## Result

