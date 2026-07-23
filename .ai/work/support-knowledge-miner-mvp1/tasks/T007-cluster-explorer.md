# Task T007: Clustering foundation, cluster explorer, and source traceability

- Status: reviewed
- Parent requirement: support-knowledge-miner-mvp1
- Plan: `.ai/work/support-knowledge-miner-mvp1/PLAN.md`
- Depends on: T006
- Owner/agent: implementer
- Last updated: 2026-07-22

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

- [x] Spec AC-21: Clustering implementation avoids full pairwise all-record distance computation and exposes outliers/unassigned records.
- [x] Spec AC-22: Automatic values, manual overrides, and effective values are distinguishable for clusters.
- [x] Spec AC-24: Candidate/source traceability groundwork reaches original imported source fields for clusters.
- [x] Spec AC-34: Cluster explorer UI distinguishes automatic/manual/effective values and provides source drilldown.

## Implementation constraints

- Preserve source traceability on all cluster memberships.
- Do not overwrite manual values with later run output.
- Avoid tests that assert exact cluster quality on non-reference real data.

## Applicable specification and test seam

- Specification criteria: AC-21, AC-22, AC-24, AC-34.
- Primary observable boundary for this task: cluster API/service and cluster explorer UI.
- Implementation-specific boundaries to avoid testing directly: exact internal vector index implementation.

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

- Clustering algorithm choice may need later tuning; keep architecture replaceable and profile-driven.

## Result

- Added cluster and cluster-membership persistence in `0007_clusters.sql`, linked to project, analysis run, dataset version, and original `message_pairs`.
- Added `ClusterService` with idempotent generation for completed runs, a deterministic linear prefix scaffold that avoids pairwise all-record distance computation, outlier marking for singleton groups, manual override updates, and source traceability queries.
- Added authenticated cluster API routes for generate/list/update/source drilldown.
- Added Cluster Explorer UI to generate/load clusters, distinguish automatic/manual/effective fields, save manual overrides, show outlier status, and drill down to original `ticketid`, `messagegroupid`, `message`, and `answer`.
- Added migration, service, API, and frontend smoke coverage for non-quadratic grouping seam, outliers, effective/manual separation, and source traceability.
- Verification observed on 2026-07-22:
  `./.ai/tools/format.sh --check`,
  `./.ai/tools/lint.sh`,
  `./.ai/tools/test.sh`,
  `./.ai/tools/security.sh`,
  `python .ai/tools/check-docs.py`,
  `./.ai/tools/verify.sh`.
