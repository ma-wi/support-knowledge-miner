# Task T005: Dokumentation, Fehlerkatalog und Verifikation

- Status: ready
- Parent requirement or change: CHG-005-PROVIDER-SETTINGS-CENTRALIZATION
- Plan: `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/PLAN.md`
- Work type: incremental-change
- Review batch: RB005
- Depends on: T002,T003,T004
- Owner/agent: Codex
- Last updated: 2026-08-05

## Objective

Reconcile durable documentation and execute focused/full verification for the
implemented change.

## Scope

- Update capability specs for provider instances, active vLLM removal, bounded
  parallel job starts, Import/Explorer behavior and feedback overlay.
- Update design system/component catalog current truth.
- Update `docs/errors/ERROR_CATALOG.md` for new stable codes.
- Run focused gates and `./.ai/tools/verify.sh`.
- Record adversarial pre-review, visual evidence and review readiness.

## Security Assurance

- Security assurance: required
- Security triggers: secrets, local-network provider calls, migration, public API
  contracts, bounded job admission and irreversible active-provider deletion.
- Assets and data classes: provider secrets, endpoint URLs, provider/model
  provenance, job metadata, historical import/indexing/cluster-set logs and error
  catalog entries.
- Trust boundaries and untrusted inputs: documentation claims, API contracts,
  frontend mappings, database migrations and provider responses as represented in
  tests.
- Authorization model: no new authorization model in this documentation slice;
  existing authenticated/project-scoped API boundaries remain current truth.
- Threats and abuse cases: stale docs re-enabling vLLM, missing error codes,
  uncatalogued unsafe failure messages, incomplete verification evidence and
  misleading provider deletion semantics.
- Mitigations: durable specs and ADRs updated, error catalog/API contract reconciled,
  vLLM searches performed, full gates rerun and verification evidence recorded.
- Security verification: T002/T003/T004 tests, user-facing error gate, UI-quality
  gate, security gate and full `verify.sh`.
- Residual security risk: historical requirements and superseded ADR text may still
  mention vLLM but are not current active behavior.
- Specialist security review: required before merge because provider secrets,
  endpoint handling, migration and hard deletion changed.

## Error and recovery implementation

### User actions covered

Documentation and verification for all changed Provider, indexing, Cluster-Set,
Import, Explorer and feedback actions.

### Expected failures

Catalog/contract mismatches, stale active vLLM documentation, missing frontend
normalization, missing API contract entries and failed focused/full gates.

### Unknown failure behavior

- User-facing fallback: not-applicable for documentation/gate work; production
  fallbacks are owned by T002-T004.
- Correlation ID: not-applicable.
- Retry behavior: correct documentation/code mismatch and rerun the failed gate.
- Input preservation: not-applicable to verification work.
- Support behavior: record residual blocker if a mandatory gate cannot run locally.

### Required negative tests

- [x] new active codes are present in catalog and frontend mapping.
- [x] provider/global-job negative paths are covered by backend/API/frontend tests.
- [x] stale active vLLM UI/API/runtime references are searched and removed or
  explicitly documented as historical only.
- [x] full verification gate is rerun after remediation.

## UI classification

- Design class: 3

## Component impact

### Existing components reused

- Maintained design documentation for the App shell, Provider forms, feedback,
  Import, Indizieren, Cluster-Sets and Explorer.

### Existing components extended

- Component catalog and design-system rules are updated to match the production UI.

### New shared components

| Name/responsibility | Target path/layer | API/variants/states | Tests | Accessibility | Story/equivalent | Catalog entry |
|---|---|---|---|---|---|---|
| none | not-applicable | not-applicable | not-applicable | not-applicable | not-applicable | not-applicable |

### New feature-local components

- Not introduced by documentation/verification work.

### Components replaced or removed

- Stale documentation for separate Settings Provider tabs and active vLLM support
  is removed or marked historical/superseded.

### Rejected reuse options

- Leaving old design documentation unchanged was rejected because it would
  contradict the implemented UI.

### Rationale

This slice reconciles maintained documentation and verifies the UI-quality contract
without adding new production components.

## Visual evidence

- Required screens: Provider, Import, Indizieren, Cluster-Sets, Explorer and
  feedback overlay.
- Required states: default, blocked, error, hidden export and conditional details.
- Required viewports: desktop/mobile.
- Manifest: to be produced by visual review if the lifecycle advances beyond
  implementation verification.

## Verification

- `UV_PYTHON=3.13 uv run --locked python -m pytest tests/api/test_provider_profile_api_integration.py tests/providers/test_provider_model_discovery.py tests/providers/test_provider_secret_storage.py tests/db/test_migrations.py tests/db/test_compose.py tests/db/test_provider_profile_smoke_script.py tests/analysis/test_analysis_service.py tests/clusters/test_cluster_service.py` — 103 passed.
- `cd frontend && npm run test` — 39 passed.
- `./.ai/tools/format.sh --check` — passed.
- `./.ai/tools/lint.sh` — passed.
- `./.ai/tools/verify.sh` — passed; includes 198 backend tests, 39 frontend tests, 5 Bats shell smoke tests, dependency audit, security scan and build.
