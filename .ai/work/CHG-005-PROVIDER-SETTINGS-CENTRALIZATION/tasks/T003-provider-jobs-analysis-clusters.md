# Task T003: Provider-IDs in Analyse/Clusterung und bounded Parallelität

- Status: ready
- Parent requirement or change: CHG-005-PROVIDER-SETTINGS-CENTRALIZATION
- Plan: `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/PLAN.md`
- Work type: incremental-change
- Review batch: RB003
- Depends on: T002
- Owner/agent: Codex
- Last updated: 2026-08-05

## Objective

Switch indexing and Cluster-Set creation to provider instance IDs, snapshot
provider provenance and allow bounded parallel indexing, Cluster-Set creation,
refinement and outlier recalculation through the existing local worker queues.

## Scope

- Indexing request/service uses provider configuration ID plus model.
- Cluster-Set request/service uses LLM provider configuration ID plus model.
- Existing run/set responses expose provider display snapshots.
- Previously planned global active-job checks are removed; cancellation remains
  available and local worker queues/resource budgets remain bounded.
- Explorer ordering uses last updated completed Cluster-Set.

## Security Assurance

- Security assurance: required
- Security triggers: provider data transfer, project-scoped data, local resource
  control.
- Assets and data classes: imported support text, provider/model provenance,
  indexing job metadata, cluster-set job metadata and project-scoped derived data.
- Trust boundaries and untrusted inputs: browser job-start payloads, provider
  configuration references, database active-job state and OpenAI/Ollama provider
  responses.
- Authorization model: existing authenticated API boundary plus project-scoped
  service checks for project resources.
- Threats and abuse cases: accidental OpenAI text transfer, unbounded parallel local
  provider/CPU/memory overload, and partial derived writes after queue overload.
- Mitigations: existing project authorization, provider config validation, cloud-use
  confirmation before OpenAI text transfer, bounded local worker queues and existing
  clustering working-set budgets.
- Security verification: service/API/frontend tests for bounded parallel starts,
  provider instance validation, cloud-use confirmation and safe Problem Details.
- Residual security risk: two local workers can still contend for local provider or
  CPU/memory capacity; queue and per-job budgets bound the risk for the MVP runtime.
- Specialist security review: use T002 specialist review unless new findings
  increase risk.

## Error and recovery implementation

### User actions covered

Indexing start and Cluster-Set create/refine/recalculate start.

### Expected failures

| Action | Failure | Error code | Safe user message | Placement | Recovery | Retry | Input preservation | Tests | Logging/correlation |
|---|---|---|---|---|---|---|---|---|---|
| Indizierung starten | local queue capacity exhausted | `UNEXPECTED_ERROR` | Die Indizierung konnte nicht gestartet werden. Bitte später erneut versuchen. | Indizierungsformular | Retry later | yes | Preserve fields | service/API/frontend | safe job reference when available |
| Cluster-Set starten | local queue capacity exhausted | `UNEXPECTED_ERROR` | Das Cluster-Set konnte nicht gestartet werden. Bitte später erneut versuchen. | Cluster-Set-Formular | Retry later | yes | Preserve fields | service/API/frontend | safe job reference when available |

### Unknown failure behavior

- User-facing fallback: safe `UNEXPECTED_ERROR` or action-specific fallback in the
  affected form/card.
- Correlation ID: safe request/job reference when available.
- Retry behavior: retry after correction or local queue capacity becomes available.
- Input preservation: preserve selected dataset/provider/model and cluster
  parameters.
- Support behavior: refresh active-job status and affected job lists.

### Required negative tests

- [x] active indexing does not block a second indexing start while queue capacity is
  available.
- [x] active Cluster-Set job does not block another root/refine/recalculate start
  while queue capacity is available.
- [x] cancellation remains available while other jobs are queued/running.
- [x] API responses use safe Problem Details without cross-project data leakage.

## UI classification

- Design class: 3

## Component impact

### Existing components reused

- Existing Indizieren form, Cluster-Set form and job cards.

### Existing components extended

- Start controls no longer use global active-job disabled states; queue errors remain
  safe feedback.
- Explorer default selection uses the existing Explorer and Cluster-Set list state.

### New shared components

| Name/responsibility | Target path/layer | API/variants/states | Tests | Accessibility | Story/equivalent | Catalog entry |
|---|---|---|---|---|---|---|
| none | not-applicable | not-applicable | not-applicable | not-applicable | not-applicable | not-applicable |

### New feature-local components

- No new standalone component in this service slice.

### Components replaced or removed

- The previously planned global job guards are removed.

### Rejected reuse options

- Client-only concurrency disabling was rejected because the backend worker queues
  are the bounded resource-control seam.

### Rationale

The bounded local worker queues are the resource-control seam; the frontend should
not block parallel starts merely because a job is already active.

## Visual evidence

- Required screens: Indizieren, Cluster-Sets and Explorer.
- Required states: parallel queued/running starts, cancel available, Explorer default.
- Required viewports: desktop/mobile in production UI evidence.
- Manifest: deferred to T004/T005 production UI verification.

## Verification

- Targeted analysis/cluster service and API tests.
- Focused frontend parallel-start tests after T004.
