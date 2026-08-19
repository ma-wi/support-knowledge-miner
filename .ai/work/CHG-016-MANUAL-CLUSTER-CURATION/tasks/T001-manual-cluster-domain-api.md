# Task T001: Manual-Cluster-Domain, Persistenz und API

- Status: draft
- Parent requirement or change: `docs/requirements/chg-016-manual-cluster-curation.md`
- Plan: `.ai/work/CHG-016-MANUAL-CLUSTER-CURATION/PLAN.md`
- Work type: incremental-change
- Review batch: RB001
- Depends on: D001–D011 owner confirmation
- Owner/agent: planner pending
- Last updated: 2026-08-19

## Objective

Den vorhandenen Cluster-/Cluster-Set-Owner um einen bounded `manual_edit`-Workflow
erweitern: leeres Cluster, beispielbasiertes LLM-Initialisieren, gezielte
Einzel-Cluster-Summary, referenzbasierte semantische Match-Vorschau und atomare
bestätigte Zuweisung. Additive API-/DB-Verträge und stabile Problem Details schaffen
den Seam für die UI.

## Scope

### In scope

- Migration für manuelle FAQ-Overrides und benötigte Manual-Edit-Version/State-
  Daten nach bestätigtem D001.
- Service-Methoden für create/preview/commit mit Projekt- und Parent-Prüfung.
- Persistierte effective/manual fields, assignment metadata, bounded source snapshot.
- Persistierte Embedding-Suche anhand message/answer und bestehender Providergrenzen.
- Structured LLM summary für Beispiele mit OpenAI-Bestätigung und Redaction.
- Einzel-Cluster-Summary mit exakt einem Cluster, bounded Sample und unveränderten
  Memberships.
- Referenzsuche mit `reference_pair_ids`, Basis, Scope, bounded Ergebnissen und
  serverseitiger Projekt-/Set-Prüfung; mehrere Referenzen nach bestätigter Regel.
- API request/response models, Problem Details, API contract and catalog entries.

### Out of scope

- React flow, inline controls and source-dialog button.
- Mutation automatically generated sets.
- New third-party matching dependency.

## Preconditions

- D001–D011 bestätigt; Designklasse bleibt mindestens 2.
- Local/test fixtures only; no production resources or data.

## Impact and responsibility

- `IMPACT.md` rows closed: API, backend schema/service, domain, persistence,
  integrations/search, telemetry, security and backend error rows.
- Existing responsibility: extend `ClusterService`, `ClusterError` and FastAPI
  cluster-set owner.
- New/parallel artifacts: only additive routes/payloads/migration fields; no second
  membership store.
- Superseded artifacts: none in this task.

## Affected files or components

`backend/clusters/service.py`, `backend/api/app.py`, migration sequence,
`docs/api/problem-details-contract.yaml`, `docs/errors/ERROR_CATALOG.md`,
`tests/clusters/`, `tests/api/`, `tests/db/` and capability specification updates.

## Acceptance criteria

- [ ] Empty/manual and example-driven modes validate mutually exclusive required data.
- [ ] LLM output for create and single-cluster refresh is bounded/schema-validated;
  provider/cloud failures are safe and refresh touches only the target cluster.
- [ ] Match scope/basis/candidate/result limits are server validated and project scoped.
- [ ] Reference pair IDs are validated against the selected cluster set; scopes mean
  current cluster, all clusters, all active or outliers exactly as documented.
- [ ] Commit creates/uses the approved manual-edit child and preserves one membership
  per pair transactionally.
- [ ] Generated parent/ordinary sets reject structural manual mutation.
- [ ] API Problem Details, catalog, contract and tests are aligned.
- [ ] Raw source/prompt/provider content is absent from diagnostics/logs/errors.

## Security Assurance

- Security assurance: required
- Security triggers: confidential support text, project API mutation, provider/
  network boundary, untrusted LLM output, resource control and migration.
- Assets/data: imported messages/answers and examples confidential; embeddings and
  membership metadata internal/confidential; provider credentials secret.
- Trust boundaries: browser/API, API/database, backend/provider, local vector work.
- Authorization model: authenticated user plus server-side project/cluster-set/pair
  ownership checks; client IDs never establish authority.
- Threats/abuse cases: cross-project IDs, prompt/response injection, raw-text logs,
  cloud transfer without consent, oversized candidate scopes, replay/conflict.
- Mitigations: parameterized project-scoped transactions, bounds/timeouts, strict
  parsers, explicit provider confirmation, redacted aggregate diagnostics,
  unique constraints and conflict/version checks.
- Security verification: negative API/service tests for each threat, redaction tests,
  migration tests and dependency/security gates.
- Residual risk: semantic false positives remain analyst-reviewed; bounded and tracked.
- Specialist security review: required before T001 is marked reviewed.

## Error and recovery implementation

### User actions covered

- Create, search/preview, confirm/commit, provider selection and reload/retry.

### Expected failures

Use the `CHANGE.md` matrix; add exact mappings for `CLUSTER_MANUAL_CREATE_INVALID`,
`CLUSTER_MANUAL_EXAMPLES_REQUIRED`, `CLUSTER_MANUAL_SUMMARY_FAILED`,
`CLUSTER_SINGLE_SUMMARY_FAILED`, `CLUSTER_MANUAL_MATCH_FAILED`,
`CLUSTER_MANUAL_MATCH_EMPTY`, `CLUSTER_REFERENCE_SELECTION_INVALID`,
`CLUSTER_REFERENCE_SEARCH_FAILED`, `CLUSTER_REFERENCE_SEARCH_EMPTY` and
`CLUSTER_MANUAL_EDIT_CONFLICT`.

### Unknown failure behavior

Central safe Problem Details with correlation; no raw text/provider/SQL/stack trace;
payloads and safe form values preserved; retry/reload available.

### Required negative tests

- [ ] Validation, auth, authorization, not-found, conflict and business-rule paths
- [ ] Provider unavailable, cloud confirmation, timeout/cancellation and malformed LLM
- [ ] Single-cluster refresh preserves neighboring clusters and all memberships
- [ ] Reference IDs/scopes, empty result and multi-reference aggregation boundaries
- [ ] Candidate/result bounds, unknown IDs, duplicate/replay and unexpected error
- [ ] Unknown code and absence of raw support text/provider bodies

### Error acceptance criteria

- [ ] Backend/API/catalog/schema mappings agree and all known paths are actionable.
- [ ] No partial membership write occurs after failed create/commit.

## Implementation constraints

Use existing ProviderService/embedding normalization and cluster-set transaction
patterns. Do not log example text, prompts, response bodies or full IDs. Do not add a
dependency without dependency-policy approval.

## Applicable capability specification and test seam

- Specification criteria: Cluster-Sets, Cluster Explorer, source traceability and
  immutable/generated lineage sections.
- Primary observable boundary: API create/preview/commit responses and persisted
  cluster/membership rows.
- Avoid testing SQL text or private implementation details where service behavior can
  be asserted through fixtures.

## Verification

- [ ] Focused service/API/migration tests
- [ ] Lint/static/security checks
- [ ] Error/catalog/contract checks
- [ ] Documentation assessment

```bash
./.ai/tools/test.sh
./.ai/tools/check-user-facing-errors.py
./.ai/tools/security.sh
```

## Risks or blockers

D001–D011 lifecycle, example, summary and reference-search semantics; exact
migration/version conflict strategy.

## UI classification

- Design class: 0
- Prototype strategy: none
- Visual review required: no

## Component impact

### Existing components reused

not-applicable: backend/API task.

### Existing components extended

not-applicable: backend/API task.

### New shared components

none

### New feature-local components

none

### Components replaced or removed

none

### Rejected reuse options

not-applicable: no UI.

### Rationale

No product UI is changed in this task.
