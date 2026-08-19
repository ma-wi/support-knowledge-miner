# Change impact: Manuelle Cluster-Kuration und direkte Explorer-Bearbeitung

- Change ID: CHG-016-MANUAL-CLUSTER-CURATION
- Status: draft
- Change request: `.ai/work/CHG-016-MANUAL-CLUSTER-CURATION/CHANGE.md`
- Last updated: 2026-08-19

## Search scope and current-state findings

Untersucht wurden `.ai/project.yaml`, `PROJECT_CONTEXT.md`, die Lifecycle-/UI-/Fehler-
und Security-Policies, `docs/specifications/support-knowledge-miner-mvp1.md`,
`docs/architecture/overview.md`, `backend/api/app.py`, `backend/clusters/service.py`,
`backend/analysis/service.py`, `backend/providers`, Migrationen 0004, 0006, 0007,
0015, 0016, 0020, `frontend/src/App.tsx`, `frontend/src/App.css`, API-/Service-/UI-
Tests, Error Catalog und Design-System. Der Arbeitsbaum enthält bereits zahlreiche
uncommittete, nutzereigene Änderungen; diese Planung klassifiziert den aktuellen
Stand und überschreibt nichts davon.

## Impact matrix

| Layer or concern | Located artifact / current owner | Action | Required end state | Owning task | Verification evidence |
|---|---|---|---|---|---|
| UI and interaction state | `frontend/src/App.tsx`, Explorer table/source dialog | modify | Neuer Manual-Cluster-Flow, Einzel-Cluster-LLM-Refresh, Referenzauswahl/-suche, Inline-Autosave, Source-Move | T002/T003 | React + Browser/A11y/Visual |
| Frontend validation and feature model | API-Typen, `ApiCluster`, `Cluster`, `ERROR_MESSAGES_BY_CODE` | modify | Manuelle FAQ-Felder, Match-/Move-Zustände, Rollback | T002/T003 | typecheck, component tests |
| API client / generated artifacts | Fetch-Aufrufe in `App.tsx`; kein separater Generator gefunden | modify | Zentraler API-Fehlerpfad und neue typed payloads/responses | T001/T002/T003 | contract/frontend tests |
| Public API or message contract | FastAPI `/api/projects/*/clusters`, `/cluster-sets/*` | modify | Create/preview/move, Einzel-Summary und Referenzsuche, erweiterter PATCH, Problem Details | T001 | API contract tests |
| Backend schema and application service | `backend/api/app.py`, `backend/clusters/service.py` | modify | Projektbezogene, transaktionale manual-edit operationen | T001/T003 | service/API tests |
| Domain model and business rules | `Cluster`, `ClusterSet`, `ClusterMembership`, `manual_edit` | modify | Empty/manual clusters, one-membership invariant, manual child lifecycle | T001/T003 | domain/service tests |
| Persistence and migration | migrations 0007, 0015, 0020; PostgreSQL | migrate | Nullable manual FAQ overrides, version/conflict metadata if needed | T001 | migration/persistence tests |
| Integrations, jobs, events, caches, search | ProviderService, Analysis embeddings, cluster-set events | modify | Bounded Einzel-Summary, Referenz-/Embedding-Suche und auditable events | T001/T003 | provider/error/resource tests |
| Telemetry and operations | audit events and restricted cluster diagnostics | modify | Aggregate bounded diagnostics; no raw text/full IDs | T001/T003 | redaction/logging tests |
| Tests and fixtures | `tests/api/test_cluster_api_integration.py`, `tests/clusters/test_cluster_service.py`, `frontend/src/App.test.tsx` | modify | Positive, boundary, conflict, rollback, auth, provider and UI coverage | T001/T002/T003 | focused gates + verify |
| Documentation and specifications | MVP spec, error catalog, API contract, README/context assessment | modify | Current manual curation and direct edit behavior documented in place | T001/T002/T003 | docs check + orphan search |
| Security assurance | project-scoped API, support text, LLM/provider, mutation | modify | Threat mitigations and negative evidence complete | T001/T002/T003 | security gate + specialist review |
| Backend domain errors | `ClusterError`, cluster Problem Details mapper | modify | Stable codes for validation, provider, match, conflict and move failures | T001/T003 | API negative tests |
| Backend exception mapping | `_cluster_problem_response` / central safe fallback | modify | No raw SQL/provider/text/stack details cross boundary | T001/T003 | unexpected/error mapping tests |
| HTTP problem response | `backend/api/app.py`, `docs/api/problem-details-contract.yaml` | modify | New codes, suggested actions, field identities and safe correlation | T001 | contract tests |
| API contract | Problem Details catalog and endpoint schemas | modify | New request/response payloads documented and backward compatible | T001 | schema/contract tests |
| Error catalog | `docs/errors/ERROR_CATALOG.md` | modify | Create, Einzel-Summary, Referenzsuche und Move-Einträge mit Mapping-Audit | T001/T002/T003 | `check-user-facing-errors.py` |
| Generated client error types | No generated client; central TS normalizer owns mapping | modify | New stable code mappings in central path | T002/T003 | frontend mapping tests |
| Frontend error normalization | `normalizeApiError`, `actionErrorMessage` | modify | All new API failures use central normalization | T002/T003 | component negative tests |
| Error-code mapping | `ERROR_MESSAGES_BY_CODE` | modify | One safe actionable mapping per new code | T002/T003 | mapping tests |
| Field error rendering | inline table cells and create form | modify | Correct fields receive validation errors and retain input | T002 | UI tests |
| Form-level error rendering | manual create/preview and single-summary flow | modify | Provider/match/create/refresh failures remain visible in the flow | T002 | UI/browser tests |
| Component-level error state | source dialog, reference preview and cluster refresh | modify | Partial failures do not blank unrelated Explorer state | T002/T003 | UI tests |
| Page-level error state | Explorer load/reload | keep | Existing safe fallback remains authoritative | T002/T003 | regression tests |
| Toast or transient feedback | global feedback overlays | modify | Success only after commit; status feedback for autosave/move | T002/T003 | no-false-success tests |
| Input preservation | inline draft, create form, search filters, source list | modify | Failed writes retain safe values and selections | T002/T003 | rollback tests |
| Retry and recovery actions | existing reload/retry patterns | modify | Retry/reload/correct-input paths per action | T001/T002/T003 | negative tests |
| Logging and correlation | audit/service loggers | modify | Correlation and aggregate metadata only | T001/T003 | redaction tests |
| Negative-path tests | API/service/frontend test suites | modify | Auth, not-found, conflict, invalid input, provider, timeout, unknown code | T001/T002/T003 | focused + full verify |
| Browser or visual error evidence | UI quality commands and `.ai/work/.../evidence/ui` | modify | Class-2 flow, Einzel-Summary, Referenzsuche, inline/source errors, mobile/desktop and focus evidence | T002/T003 | browser/A11y/visual review |
| Error-handling documentation | CHANGE + capability spec + catalog | modify | One current contract without orphan codes | T001/T002/T003 | docs/error gate |

## New or parallel artifacts

| Proposed artifact | Existing responsibility searched | Why extension/replacement is insufficient | Compatibility need | Removal criterion |
|---|---|---|---|---|
| New manual-cluster create/preview API routes under existing cluster-set owner | `ClusterSetRequest`, cluster-set routes, `ClusterService` | Existing refinement request cannot represent empty/manual metadata or similarity preview | Existing routes remain for normal/refinement cluster sets | Remove only if one existing route can express the complete contract without ambiguous modes |
| Single-cluster summary refresh route under existing cluster owner | `ClusterSetSummaryRequest`, summary service and cluster PATCH | Existing summary regeneration targets a whole set and PATCH does not invoke an LLM | Existing set-summary route remains unchanged | Remove if the existing summary route gains an unambiguous single-target mode |
| Reference-search route under existing source/cluster-set owner | `list_sources`, embedding loaders and Explorer search | Existing source GET only pages one cluster and cannot accept references/basis/scope | Existing source paging remains | Remove if an existing search contract can express bounded reference search without ambiguity |
| New manual source-move route under existing cluster/source owner | `list_sources`, cluster PATCH, cluster-set mutation service | Existing source GET and cluster PATCH cannot atomically move one pair to Outliers | Existing source GET remains | Remove if a single existing mutation contract replaces it without weakening semantics |
| Inline feature-local edit state/preview composition | Existing `App.tsx` table/dialog patterns | New multi-step flow and field-level rollback need isolated state | No shared global state dependency | Consolidate into a shared component only if reuse is demonstrated in a later feature |

## Conditional impact annexes

## UI classification

- Design class: 2
- Rationale: New multi-step manual-cluster creation/preview flow and new source-dialog
  action; inline editing reuses the established Explorer table/dialog composition.
- Highest design class assigned: 2
- Implementation-start design class: not-started
- Prototype strategy: isolated-prototype or approved React mock prototype
- Prototype artifact/revision: pending design review
- Required tool dependencies and owning package: existing frontend UI-quality package
- Existing pattern/components reused: Explorer table, source dialog, form controls,
  status chips, feedback overlays and modal focus handling.
- Applicable design-system rule: established table/dialog/form/feedback/accessibility
  rules in `docs/design/DESIGN_SYSTEM.md`.
- Design approval status: pending
- Visual review required: yes
- Required screens: manual-cluster form; example/LLM loading/error; single-cluster
  refresh; reference selection/search preview; empty cluster result; inline edit
  success/error; source move success/error.
- Required viewports: configured desktop 1440x1000 and mobile 390x844.

## Component impact

### Existing components reused

- Existing Explorer table and sortable headers.
- Existing source dialog with focus trap, pagination and sticky header.
- Existing semantic form controls, feedback overlay, status chips and error regions.

### Existing components extended

- Feature-local Explorer row editing to support FAQ fields and autosave state.
- Source dialog rows to expose move-to-outlier action.
- Explorer control rail or existing action area for manual cluster creation.

### New shared components

none proposed; component creation requires a new reuse search and catalog decision.

### New feature-local components

- Manual cluster creation/preview composition, only if keeping it inside `App.tsx`
  would violate one-responsibility or accessibility boundaries.

### Components replaced or removed

- Existing per-row `Speichern` form controls: remove after inline autosave has
  equivalent validation, focus and rollback coverage.

### Rejected reuse options

- Separate global editor page: would duplicate the Explorer owner and break the
  requested direct workflow.
- New component library: no demonstrated responsibility beyond current primitives.

### Rationale

The change extends established Explorer patterns and introduces only one new
feature-local composition for the multi-step flow.

## Superseded artifacts

| Artifact | Disposition: remove/deprecate/replace/retain | Reason if retained | Owning task | Removal criterion or evidence |
|---|---|---|---|---|
| Row-level `Speichern` button/form | remove/replace | Replaced by field-level autosave | T002 | UI search and regression tests show no stale control |
| Auto-summary-only editing assumption | replace | Manual FAQ override fields become current behavior | T001/T002 | Capability spec and API search updated |
| Direct structural mutation of generated set | retain as forbidden invariant | Generated sets remain immutable | T001/T003 | Service negative tests |

## Concept-trace completion

- Repository-wide search terms and symbols: `manual_edit`, `cluster_memberships`,
  `auto_summary_question`, `auto_summary_answer`, `ClusterUpdateRequest`,
  `list_sources`, `sourceDialog`, `assignment_type`, `embeddings`, `vector_basis`,
  `LLM_PROVIDER_UNAVAILABLE`, `CLUSTER_MANUAL_UPDATE_INVALID`, `Speichern`,
  `summary regeneration`, `reference`, `similarity`, `sourceDialog`.
- Generated sources traced to authoritative input: not-applicable; no generated API
  client was found.
- No relevant references remain unclassified: yes for planning scope.
- Uncertainty: D001–D011, final endpoint names, migration version and exact provider
  query strategy require Readiness confirmation.

## Acceptance

- Impact analysis complete: no
- Accepted by:
- Date:
