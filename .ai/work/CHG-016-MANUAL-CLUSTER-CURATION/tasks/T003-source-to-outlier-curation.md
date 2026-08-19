# Task T003: Quellen einzeln in Outliers verschieben

- Status: draft
- Parent requirement or change: `docs/requirements/chg-016-manual-cluster-curation.md`
- Plan: `.ai/work/CHG-016-MANUAL-CLUSTER-CURATION/PLAN.md`
- Work type: incremental-change
- Review batch: RB003
- Depends on: T001, D001 owner confirmation
- Owner/agent: planner pending
- Last updated: 2026-08-19

## Objective

Den bestehenden Source-Dialog um eine einzelne, atomare und sichere
„In Outliers verschieben“-Aktion erweitern. Der manuelle Child-Zustand bleibt
projektbezogen nachvollziehbar; der Ursprung bleibt bei generierten Sets unverändert.

## Scope

### In scope

- Per-source move action and API mutation under the existing source/cluster owner.
- Create/reuse of a dedicated Outlier cluster in the mutable manual child.
- Remove source from origin membership and insert manual outlier membership in one
  transaction; preserve empty origin cluster and trace metadata.
- Refresh cluster counts, source dialog page and Explorer state after success.
- Conflict/not-found/permission/replay/rollback behavior and browser evidence.

### Out of scope

- Similarity preview or manual cluster form (T001/T002).
- Deleting source records or changing original imported text.

## Preconditions

D001 confirms mutable manual child semantics; T001 exposes the mutation contract.

## Impact and responsibility

- `IMPACT.md` rows closed: domain membership, source dialog, API errors, recovery,
  audit/telemetry and security.
- Existing responsibility: extend `ClusterService.list_sources` owner and source
  dialog; no parallel source assignment store.
- Superseded artifacts: none; existing read-only source dialog becomes actionable.

## Affected files or components

`backend/clusters/service.py`, `backend/api/app.py`, migrations only if T001 needs
state/version support, `frontend/src/App.tsx/.css`, API/service/frontend tests,
capability spec and UI evidence.

## Acceptance criteria

- [ ] Each source row exposes an accessible move action when valid.
- [ ] A successful move leaves exactly one membership for the pair, with
  `assignment_type=manual`, `is_outlier=true` and bounded reason metadata.
- [ ] Existing or newly created Outlier cluster is visible and counts refresh.
- [ ] Generated non-manual sets reject the mutation without changing data.
- [ ] Conflict, stale pair, unauthorized project, duplicate retry and transaction
  failure preserve source UI and show no false success.
- [ ] Empty source clusters remain represented for lineage; source data is never
  deleted.

## Security Assurance

- Security assurance: required
- Security triggers: confidential source text, project-scoped destructive-looking
  mutation, concurrency/replay and audit data.
- Assets/data: message pair, cluster membership and project lineage internal/confidential.
- Trust boundaries: browser/API/database; client-supplied cluster/pair IDs untrusted.
- Authorization model: authenticated project owner check in service/database query;
  no client-only source visibility or permission decision.
- Threats/abuse cases: cross-project move, moving a pair twice, mutating generated set,
  concurrent overwrite, source text leakage in errors/logs.
- Mitigations: project-scoped transaction, parent/child/type check, unique constraint,
  idempotent re-read, optimistic version/conflict response, redacted audit metadata.
- Security verification: API auth/project isolation tests, replay/concurrency tests,
  generated-set rejection and log/error redaction assertions.
- Residual risk: manual move is reversible only through a later manual move/include
  operation; retain lineage and provide reload recovery.
- Specialist security review: required with T001/T002 independent review.

## Error and recovery implementation

### User actions covered

- Load sources, move source, retry/reload and close/reopen dialog.

### Expected failures

Use `CLUSTER_MANUAL_SOURCE_MOVE_FAILED` for transaction/dependency failure and
`CLUSTER_MANUAL_EDIT_CONFLICT` for stale manual child/version; existing not-found,
auth and source-page codes remain consistent.

### Unknown failure behavior

Central safe fallback in the dialog; source remains in the prior displayed state;
correlation reference and retry/reload only.

### Required negative tests

- [ ] Auth/project isolation, not-found, generated-set rejection and stale conflict
- [ ] Duplicate/replay, transaction failure, provider-independent network failure
- [ ] Unknown code, rollback, no false success, source text redaction

### Error acceptance criteria

- [ ] The source action is disabled while pending and recovered after failure.
- [ ] The dialog retains loaded rows/filters and announces success only after commit.

## UI classification

- Design class: 1 within approved class-2 composition
- Prototype strategy: reuse approved class-2 source-dialog extension
- Visual review required: yes

## Component impact

### Existing components reused

Source dialog, sticky header, paged source list, focus trap, feedback/live regions and
secondary/destructive action styles.

### Existing components extended

Source row action group and source-dialog refresh state.

### New shared components

none

### New feature-local components

none unless the action state cannot remain local to the source row.

### Components replaced or removed

none

### Rejected reuse options

No separate source-management page; the source dialog is the existing responsibility.

### Rationale

The requested action is source-local and should remain next to the evidence being
reviewed.

## Prototype relationship

- Prototype artifact: approved T002/class-2 source-dialog state
- Elements to promote: source-row action, pending/error/success state
- Prototype-only elements to discard: mock data/wiring
- Tool dependencies and owning package: existing frontend UI-quality package

## Visual evidence

- Required screens: source dialog with action, pending, success, failure and refreshed
  outlier state
- Required states: desktop/mobile/focus/long source text/error/no-false-success
- Required viewports: 1440x1000 and 390x844
- Manifest: `.ai/work/CHG-016-MANUAL-CLUSTER-CURATION/evidence/ui/manifest.json`

## Implementation constraints

Use one database transaction and server-side project/type checks. Never delete the
message pair. Never log raw source text or full ID lists.

## Applicable capability specification and test seam

- Specification criteria: source dialog, outlier management, membership traceability
  and manual-edit lifecycle.
- Primary observable boundary: source mutation response plus refreshed cluster/source
  view and persisted one-membership invariant.
- Avoid asserting implementation-specific SQL ordering; assert domain outcome.

## Verification

- [ ] focused service/API/frontend tests
- [ ] security/redaction/error checks
- [ ] browser/accessibility/visual states
- [ ] full `./.ai/tools/verify.sh` after all tasks

```bash
./.ai/tools/test.sh
./.ai/tools/security.sh
./.ai/tools/ui-quality.sh browser
```

## Risks or blockers

D001 is the main lifecycle blocker; visual density of per-source actions on mobile
must be resolved in the approved design.
