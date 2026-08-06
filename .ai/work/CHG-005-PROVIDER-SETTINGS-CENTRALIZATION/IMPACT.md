# Change impact: Provider-Einstellungen zentralisieren

- Change ID: CHG-005-PROVIDER-SETTINGS-CENTRALIZATION
- Status: accepted
- Change request: `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/CHANGE.md`
- Last updated: 2026-08-05

## Search scope and current-state findings

Searched:

- `frontend/src/App.tsx`, `frontend/src/App.css`
- `backend/providers/service.py`, `backend/api/app.py`
- `backend/db/migrations/0005_providers_profiles.sql`
- `backend/db/migrations/0015_cluster_sets_llm_summaries.sql`
- `backend/analysis/service.py`, `backend/clusters/service.py`
- `docs/specifications/local-runtime-providers.md`
- `docs/specifications/support-knowledge-miner-mvp1.md`
- `docs/design/DESIGN_SYSTEM.md`, `docs/design/COMPONENT_CATALOG.md`

Relevant findings:

- `provider_configurations.provider` is the primary key; current storage permits one
  OpenAI, one Ollama and one vLLM configuration.
- Current action requests store/select provider by string and model by string.
- Existing provider cards are feature-local in the monolithic app shell.
- vLLM is visible in current Settings and Indizieren flow.
- Current Ollama pull endpoint returns after completion and does not expose streaming
  progress.
- Global feedback is rendered inside `.content`, causing layout reflow.

## Impact matrix

| Layer or concern | Located artifact / current owner | Action | Required end state | Owning task | Verification evidence |
|---|---|---|---|---|---|
| UI and interaction state | `frontend/src/App.tsx`, `frontend/src/App.css` | modify | Single Provider tab, overlay feedback, no visible vLLM, Import/Explorer and parallel-job UI updates; Explorer loaded state uses a left control rail and top-right global menu overlay | T004,T008 | Pending implementation |
| Frontend validation and feature model | `ProviderConfiguration`, `SettingsTab`, `ConfigurableProvider`, provider selection state in `frontend/src/App.tsx` | modify | Provider instances use stable IDs/display names, available model lists and selected Embedding/LLM allow-lists; vLLM removed from active options | T004 | Pending implementation |
| Global navigation and session actions | App shell topbar/sidebar/sign-out action in `frontend/src/App.tsx`, `frontend/src/App.css` | modify | Persistent global sidebar and standalone Abmelden button are replaced in the Explorer target by a top-right menu button whose overlay contains Projekte, Einstellungen and Abmelden | T008 | Planned; no implementation authorized |
| Explorer controls composition | Explorer table, filter controls, outlier box, export panel and Cluster-Set selection in `frontend/src/App.tsx`, `frontend/src/App.css` | modify | Loaded Explorer uses a left control rail for Cluster-Set selection, search/filter, outlier controls, Summary regeneration and export; table remains the main right-side workspace with visible actions | T008 | Planned; no implementation authorized |
| Summary regeneration interaction state | Cluster-Set card Summary action, Explorer controls and Summary-only endpoint calls in `frontend/src/App.tsx` | modify | Cluster-Sets open an Option-A dialog; Explorer exposes the same Summary-only action in the control rail; default write behavior replaces current summaries unless later version/copy semantics are accepted | T008 | Planned; no implementation authorized |
| API client / generated artifacts | Direct `apiRequest` calls in `frontend/src/App.tsx` | modify | Calls address provider instances rather than only provider type | T004 | Pending implementation |
| Public API or message contract | `/api/providers`, `/api/llm-providers`, `/api/providers/{provider}`, `/api/providers/ollama/pull` | modify | Provider API supports list/add/update/remove/check/pull per provider instance, explicit available models and separate Embedding/LLM allow-lists; obsolete LLM-provider tab endpoint is left only as compatibility surface while active UI no longer uses it | T002 | API/service/frontend tests |
| Backend schema and application service | `ProviderSettingsInput`, `ProviderConfiguration`, `ProviderService` | modify | Provider configuration represents multiple instances with type, display name, available models and model allow-lists; active vLLM validation/runtime removed | T002 | Pending implementation |
| Domain model and business rules | Provider/model selection in analysis and cluster services | modify | Analysis/cluster creation uses provider instance IDs and records provider-type/display-name/model provenance snapshots | T003 | Pending implementation |
| Indexing provider input normalization | `backend/analysis/service.py`, Indizierungsformular in `frontend/src/App.tsx` | modify | Optional line-break removal/replacement and lowercasing are applied only to provider input; original texts remain unchanged and selected normalization is persisted in run parameters/embedding metadata | T003,T004 | service/API/frontend tests |
| Persistence and migration | `provider_configurations`, `analysis_runs`, `cluster_sets` migrations | migrate | Replace type primary key with stable ID plus provider type; add `available_models`; remove active vLLM configurations and obsolete purpose flags; add provenance snapshot columns | T002,T003 | Pending implementation |
| Integrations, jobs, events, caches, search | Ollama pull flow in `ProviderService`; analysis/cluster runners | modify | Simple one-active Ollama pull guard with final success/failure; remove planned global indexing/Cluster-Set start guards and rely on bounded worker queues/resource checks | T002,T003 | Pending implementation |
| Telemetry and operations | Audit event `provider.configure` | modify | Audit add/remove/rename/available-model/model-allow-list changes with redacted metadata and instance ID | T002 | Pending implementation |
| Tests and fixtures | Provider API/service tests, analysis/cluster tests, frontend tests, migration tests | modify | Tests cover instance identity, vLLM removal, checkbox selection/order, connection tests, discovery reconciliation, overlay feedback, Import date/details, Explorer default/empty, bounded parallel starts | T002,T003,T004 | Pending implementation |
| Documentation and specifications | Provider specs, MVP spec, design docs | modify | Specs and catalog describe central Provider tab, instance IDs, available models, provenance and bounded parallel job starts | T005 | Pending implementation |
| User-facing error mapping | Provider save/check/pull/delete, start indexing, start Cluster-Set | modify | Known failures have stable codes/mappings, form placement, input preservation and no false success | T002,T003,T004,T005 | Pending implementation |
| backend domain errors | Provider, analysis and cluster services | modify | Domain services raise stable codes for validation and provider deletion/pull conflicts; queue overload remains safe generic retry | T002,T003 | service tests |
| backend exception mapping | `backend/api/app.py` | modify | FastAPI maps provider exceptions to safe Problem Details | T002,T003 | API tests |
| http problem response | `backend/api/app.py` Problem Details payloads | modify | Responses include code, retryability, suggested action and safe detail | T002,T003 | API tests |
| api contract | `docs/api/problem-details-contract.yaml` | modify | Contract lists new Provider codes and removes superseded global job-guard codes | T005 | user-facing error gate |
| error catalog | `docs/errors/ERROR_CATALOG.md` | modify | Catalog declares active new codes and recovery behavior | T005 | user-facing error gate |
| generated client error types | No generated frontend client | not-applicable | Direct `apiRequest` has no generated error types to update | T004 | not-applicable |
| frontend error normalization | `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE` | modify | New codes map through central normalizer with safe unknown fallback | T004 | frontend tests |
| error-code mapping | Backend/API/frontend mappings | modify | Codes stay consistent across service, Problem Details and UI text; superseded job-guard codes are removed from active mappings | T002,T003,T004,T005 | API/frontend/error-gate tests |
| field error rendering | Provider forms | keep | No new field-level renderer; safe form-level/provider-card feedback preserves input | T004 | frontend tests |
| form-level error rendering | Provider, Indizieren and Cluster-Set forms | modify | Known failures render at actionable forms/cards plus overlay | T004 | frontend tests |
| component-level error state | Provider card, Import list and Explorer | modify | Pull/check/import-details/export-hidden states are component-scoped | T004 | frontend tests |
| page-level error state | Settings/Explorer empty states | modify | Explorer no-cluster state and provider-list failures remain safe and actionable | T004 | frontend tests |
| toast or transient feedback | Global feedback component | modify | Feedback moves to overlay with close and auto-dismiss | T004 | frontend tests |
| input preservation | Provider and job forms | modify | Safe non-secret fields, available-model order and selections survive validation/queue failures | T004 | frontend tests |
| indexing normalization input preservation | Indizierungsformular | modify | Line-break normalization selections and replacement value remain controlled user input and are sent only when enabled | T004 | frontend test |
| retry and recovery actions | Provider/job actions | modify | Correct/retry/wait/reload recovery is explicit in UI and catalog | T002,T003,T004,T005 | API/frontend/error-gate tests |
| logging and correlation | Audit and Problem Details | modify | Provider/job diagnostics use safe references and redacted metadata | T002,T003,T005 | API/security tests |
| negative-path tests | Backend/API/frontend tests | modify | vLLM rejection, provider errors and removed global guard behavior are covered | T002,T003,T004 | test wrapper |
| browser or visual error evidence | UI quality artifacts | modify | Design artifacts require Provider/feedback/parallel-job states | T004,T005 | UI-quality gate |
| error-handling documentation | CHANGE/PLAN/tasks/catalog/specs | modify | Error matrix, catalog and specs describe current recovery behavior | T005 | check-user-facing-errors.py |

## New or parallel artifacts

| Proposed artifact | Existing responsibility searched | Why extension/replacement is insufficient | Compatibility need | Removal criterion |
|---|---|---|---|---|
| `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/prototype/settings-provider-centralization-mockup.html` | Existing production UI in `frontend/src/App.tsx` | Production implementation is intentionally blocked until design direction and provider identity decisions are accepted | Temporary design-only artifact | Delete at closeout or retain as approved design reference with owner |
| `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/prototype/project-workflow-adjustments-mockup.html` | Existing Import, Explorer, Indexing and Cluster-Set UI in `frontend/src/App.tsx` | Production implementation needs behavior/API decisions and tests first | Temporary design-only artifact | Delete at closeout or retain as approved design reference with owner |
| `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/prototype/cluster-summary-explorer-optimization-mockup.html` | Existing App shell, Explorer, Cluster-Set tree and Summary-only UI in `frontend/src/App.tsx` | Production implementation needs accepted navigation semantics, Summary write-mode semantics and UI tests first | Temporary design-only artifact | Delete at closeout or retain as approved design reference with owner |

## Conditional impact annexes

## Component impact

### Existing components reused

- App shell layout, topbar, sidebar, page tabs, panel/provider card styling.
- Existing feedback/status visual language.
- Existing checkbox model-selection pattern from OpenAI provider UI.

### Existing components extended

- Provider forms: central provider-instance management with connection controls,
  explicit connection test, available-model discovery and purpose-specific model
  checkbox groups in the same card.
- Feedback message: same visual style, fixed overlay placement.
- Import panels: protocol date and conditional details action.
- Explorer/export panel: default Cluster-Set loading and no export when empty.
- Explorer control rail: loaded Explorer state owns Cluster-Set switching,
  search/filter, outlier controls, Summary regeneration and export.
- App shell/topbar: global navigation moves behind a top-right menu button in the
  Explorer target; overlay entries are Projekte, Einstellungen and Abmelden.
- Cluster-Set cards: Summary regeneration stays as a compact action that opens a
  dialog.
- Indexing/Cluster-Set panels: bounded queued/running states with cancel action,
  without global start disabling.

### New shared components

None in this mockup. Future production implementation may justify shared provider
card or model allow-list components after reuse analysis.

### New feature-local components

- Provider instance card.
- Ollama download progress row.
- Provider connection-test action.
- Feedback overlay container.
- Import protocol row with date/details availability.
- Explorer empty/default state.
- Explorer control rail.
- Global navigation overlay menu.
- Cluster-Set Summary regeneration dialog.
- Parallel queued/running job state.

### Components replaced or removed

- Free-text „OpenAI LLM-Modelle“ field should be removed.
- Visible/active vLLM UI/backend support should be removed from the redesigned active
  product path.
- Right-side Explorer export column in loaded Explorer state should be replaced by
  the Explorer control rail export group.
- Persistent global sidebar in the Explorer workspace should be replaced by the
  top-right menu overlay.
- Standalone `Abmelden` topbar button should move into the top-right menu overlay.

### Rejected reuse options

- Keeping separate Embedding/LLM settings tabs is rejected because provider settings
  should have one visible owner.
- Using free-text model lists for Ollama/OpenAI LLM is rejected because it remains
  inconsistent with the OpenAI checkbox model.

### Rationale

The mockups keep the existing dense card/tab language while centralizing provider
ownership and clarifying project workflow states.

## Superseded artifacts

| Artifact | Disposition: remove/deprecate/replace/retain | Reason if retained | Owning task | Removal criterion or evidence |
|---|---|---|---|---|
| Current visible/active vLLM support | remove | Historical provenance may remain readable | T002,T004 | No vLLM selectable/callable unless reaccepted |
| OpenAI LLM free-text input | remove | Superseded by checkbox allow-list | T004 | No visible free-text field in LLM provider UI |
| Ollama LLM free-text input | replace | Superseded by checkbox allow-list | T004 | Ollama model selection uses checkbox list |
| Separate Embedding-/LLM-Provider Settings tabs | remove | Superseded by single Provider tab | T004 | Only Provider and Nutzer remain in Settings |
| Content-flow global feedback | replace | Same message component, different placement | T004 | Feedback no longer changes `.content` layout height |
| Explorer export panel in no-cluster state | remove from empty state | Export remains available when a Cluster-Set is loaded | T004 | No Export panel while Explorer has no Cluster-Set |
| Explorer right-side export column | replace | Superseded by left Explorer control rail export group | T008 | Loaded Explorer has no separate right export column |
| Persistent global sidebar in Explorer workspace | replace | Superseded by top-right menu overlay | T008 | Explorer target has menu button instead of persistent global sidebar |
| Standalone topbar `Abmelden` button | replace | Sign out moves into the top-right menu overlay | T008 | Abmelden appears in global overlay menu |
| Provider purpose flags | remove | Usage is derived from non-empty Embedding/LLM allow-lists | T002,T004 | No active UI/API/service/DB dependency on `supports_embedding` or `supports_llm` |
| Global indexing/Cluster-Set start guards | remove | Existing bounded workers and job states support parallel starts | T003,T004 | No backend lock/check and no frontend disabled state for active jobs |

## Concept-trace completion

- Repository-wide search terms and symbols: `ProviderConfiguration`,
  `provider_configurations`, `manual_models`, `embedding_models`, `llm_models`,
  `llm_provider`, `available_models`, `supports_embedding`, `supports_llm`,
  `ConfigurableProvider`, `SettingsTab`, `feedback`, `vllm`, `pull_ollama_model`,
  `INDEXING_ALREADY_RUNNING`, `CLUSTER_SET_ALREADY_RUNNING`.
- Generated sources traced to their authoritative input: not-applicable
- No relevant references remain unclassified: yes
- Uncertainty or intentionally excluded areas: Prozentgenauer Ollama-Fortschritt is
  intentionally excluded by accepted scope.

## Acceptance

- Impact analysis complete: yes
- Accepted by: Product Owner
- Date: 2026-08-05
