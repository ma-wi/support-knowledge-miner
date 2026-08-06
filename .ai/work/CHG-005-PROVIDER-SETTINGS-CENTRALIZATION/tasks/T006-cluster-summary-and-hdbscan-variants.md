# Task T006: Cluster-Summary-Neuerstellung und HDBSCAN-Varianten

- Status: verified
- Parent requirement or change: CHG-005-PROVIDER-SETTINGS-CENTRALIZATION
- Plan: `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/PLAN.md`
- Work type: incremental-change
- Review batch: RB006
- Depends on: T003,T004
- Owner/agent: Codex
- Last updated: 2026-08-05

## Objective

Allow LLM summaries to be regenerated for an existing completed Cluster-Set
without recalculating clusters, expose safe provider failure details, improve
Cluster-Set progress phases around expensive estimator work, and add optional
PCA/UMAP plus `auto`/`cpu`/`cuml` HDBSCAN parameters.

## Scope

- OpenAI LLM summary calls use the Responses API.
- Provider errors stored on Cluster-Sets preserve sanitized failure details.
- Completed Cluster-Sets with stored LLM provider/model can queue a summary-only
  regeneration job.
- Summary-only failures keep existing clusters and mark only the summary error.
- HDBSCAN accepts optional PCA/UMAP reduction and execution backend parameters.
- `auto` attempts cuML when available and falls back to CPU; `cuml` reports a safe
  unavailable-accelerator error when the runtime cannot provide it.
- Cluster-Set progress moves from loading to reducing/clustering before expensive
  estimator execution and to persisting before DB writes.

## Security Assurance

- Security assurance: required
- Security triggers: provider data transfer, local GPU/runtime dependency loading,
  user-observable errors and derived-data job execution.
- Assets and data classes: imported support text used in LLM prompts, provider/model
  configuration IDs, Cluster-Set assignments, local runtime capability details.
- Trust boundaries and untrusted inputs: browser summary/parameter payloads,
  OpenAI/Ollama responses, optional local cuML/UMAP imports.
- Authorization model: existing authenticated project-scoped Cluster-Set routes and
  service checks.
- Threats and abuse cases: accidental OpenAI text transfer, leaking raw provider
  bodies or local stack traces, recalculating clusters when only summaries were
  intended, silently pretending HDBSCAN can guarantee a target cluster count.
- Mitigations: explicit OpenAI confirmation, sanitized ProviderError messages,
  summary-only job path, stable error codes, documented HDBSCAN limitation and
  bounded clustering budget.
- Security verification: backend/API/frontend tests, error catalog check and lint.
- Residual security risk: `auto` GPU use depends on local RAPIDS/cuML installation;
  absence falls back to CPU, while forced `cuml` is user-selected and reports a safe
  error.
- Specialist security review: required through normal CHG-005 review because the
  task affects provider data transfer.

## Error and recovery implementation

### User actions covered

Cluster-Set creation with advanced HDBSCAN parameters and Summary-only regeneration.

### Expected failures

| Action | Failure | Error code | Safe user message | Placement | Recovery | Retry | Input preservation | Tests | Logging/correlation |
|---|---|---|---|---|---|---|---|---|---|
| Summary neu erstellen | LLM model/provider unavailable | `LLM_PROVIDER_UNAVAILABLE` | Provider/Modell ist nicht verfügbar; safe detail is stored on the Cluster-Set | Cluster-Set card | Provider/model prüfen or retry | yes | Existing clusters remain | service/API/frontend | no raw provider body |
| Summary neu erstellen | Invalid LLM output | `CLUSTER_SUMMARY_FAILED` | Zusammenfassung konnte nicht erstellt werden | Cluster-Set card | Retry or choose another LLM | yes | Existing clusters remain | service/API/frontend | no raw LLM body |
| Cluster-Set erstellen | UMAP dependency missing | `CLUSTER_REDUCTION_UNAVAILABLE` | Dimensionsreduzierung ist lokal nicht verfügbar | form/card | Choose PCA/none or install UMAP | yes | Preserve parameters | service/API/frontend | no import paths |
| Cluster-Set erstellen | Forced cuML unavailable | `CLUSTER_ACCELERATOR_UNAVAILABLE` | GPU-Beschleunigung ist nicht verfügbar | form/card | Choose CPU/auto or install RAPIDS/cuML | yes | Preserve parameters | service/API/frontend | no CUDA stack trace |

### Unknown failure behavior

- User-facing fallback: safe `UNEXPECTED_ERROR` or action-specific fallback.
- Correlation ID: safe job identifier when available.
- Retry behavior: retry after parameter/runtime/provider correction.
- Input preservation: preserve Cluster-Set form settings and existing clusters.
- Support behavior: reload Cluster-Set status, inspect sanitized diagnostics and
  retry with CPU/no-reduction or a different LLM provider/model.

### Required negative tests

- [x] Summary-only API queues summary regeneration without enqueueing full
  reclustering.
- [x] HDBSCAN PCA reduces vectors before estimator execution.
- [x] Forced cuML reports `CLUSTER_ACCELERATOR_UNAVAILABLE` when runtime is missing.
- [x] Cancelling a queued Summary-only regeneration keeps the existing Cluster-Set
  completed and loadable.
- [x] OpenAI Responses output text is parsed safely.
- [x] Frontend summary button calls only the summary endpoint.

## UI classification

- Design class: 3

## Component impact

### Existing components reused

- Existing Cluster-Set form, Cluster-Set cards, feedback overlay and provider/model
  selection patterns.

### Existing components extended

- Cluster-Set form gains advanced HDBSCAN reduction/backend controls.
- Cluster-Set cards gain a Summary-only regeneration action and safer specific
  error-message display.
- Progress display reuses existing phase/progress rendering with new
  `reducing`, `clustering`, `persisting` and `queued_summary` phases.

### New shared components

| Name/responsibility | Target path/layer | API/variants/states | Tests | Accessibility | Story/equivalent | Catalog entry |
|---|---|---|---|---|---|---|
| none | not-applicable | not-applicable | not-applicable | not-applicable | not-applicable | not-applicable |

### New feature-local components

- No standalone component; feature-local controls are added inside `App.tsx`.

### Components replaced or removed

- No production component removed in this slice.

### Rejected reuse options

- Reusing full Cluster-Set creation for summary retry was rejected because it would
  recalculate cluster assignments and violate the Summary-only requirement.
- Adding a hard HDBSCAN target-cluster cap was rejected because HDBSCAN does not
  guarantee an exact cluster count.

### Rationale

The slice extends the existing Cluster-Set workflow instead of adding a parallel
clustering or summary subsystem.

## Visual evidence

- Required screens: Cluster-Set form and Cluster-Set cards.
- Required states: completed set with Summary-only button, queued summary, HDBSCAN
  PCA/UMAP/backend controls, safe LLM/reduction/accelerator error.
- Required viewports: desktop/mobile through the existing CHG-005 visual review.
- Manifest: deferred to the CHG-005 visual-review pass.

## Verification

- `PYTHONPATH=. UV_PYTHON=3.13 uv run --locked pytest tests/clusters/test_cluster_service.py tests/api/test_cluster_api_integration.py tests/providers/test_provider_model_discovery.py` — passed, 90 tests after cancel/race/retryable/progress regressions.
- `PYTHONPATH=. uv run --locked pytest tests/clusters/test_cluster_service.py` —
  passed, 46 tests after Summary-only cancel regression fix.
- `npm test -- --run src/App.test.tsx` from `frontend/` — passed, 45 tests.
- `./.ai/tools/format.sh --check` — passed.
- `./.ai/tools/lint.sh` — passed.
- `./.ai/tools/check-user-facing-errors.py` — passed.
- `./.ai/tools/verify.sh` — passed; includes work-state, incremental-change,
  user-facing-errors, UI-quality, docs, orchestration, setup, format, lint, 223
  backend tests, 45 frontend tests, 5 Bats tests, dependency policy/audit,
  security and build.

## Result

Summary-only regeneration, safe LLM diagnostics, improved Cluster-Set progress
phases and HDBSCAN PCA/UMAP/cuML parameters are implemented and covered by focused
tests.

### Adversarial pre-review

- Adversarial pre-review: passed
- Pre-review lenses: user-facing errors, provider-data security, UI quality,
  dependency/runtime behavior, clustering compatibility and cancellation behavior.
- Pre-review evidence: Summary-only endpoint does not call full Cluster-Set create;
  existing clusters remain on summary failure; ProviderError messages are sanitized;
  forced missing cuML reports `CLUSTER_ACCELERATOR_UNAVAILABLE`; UMAP missing reports
  `CLUSTER_REDUCTION_UNAVAILABLE`; OpenAI calls use Responses API and do not expose
  raw provider bodies.
- Open P0/P1 findings: none

### Independent review

- First review found P1/P2 issues in cancel/status, summary timestamp, validation,
  and HDBSCAN diagnostics.
- Follow-up read-only review after fixes: no open P0/P1/P2 findings.
