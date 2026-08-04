# Change impact: Analystenorientierte Indizierungs- und Clusteranalyse

- Change ID: CHG-004
- Status: accepted
- Change request: `.ai/work/chg-004-analyst-clustering-redesign/CHANGE.md`
- Last updated: 2026-08-04

## Search scope and current-state findings

Searched:

- `frontend/src/App.tsx`
- `backend/api/app.py`
- `backend/providers/service.py`
- `backend/analysis/service.py`
- `backend/clusters/service.py`
- `backend/candidates/service.py`
- `backend/db/migrations/0005_providers_profiles.sql`
- `backend/db/migrations/0006_analysis_runs.sql`
- `backend/db/migrations/0007_clusters.sql`
- `backend/db/migrations/0008_candidates.sql`
- `docs/specifications/support-knowledge-miner-mvp1.md`
- `docs/specifications/local-runtime-providers.md`
- `docs/architecture/decisions/ADR-0003-analysis-profile-model-providers.md`
- tests under `tests/api`, `tests/analysis`, `tests/clusters`, `tests/candidates`,
  `tests/providers`, `tests/db`

Findings:

- Analysis profiles are a cross-layer concept: UI form/list, API routes, provider
  service, schema, tests, MVP spec and ADR-0003.
- Analysis runs are the current embedding/indexing owner and persist one message
  embedding per message pair.
- Clusters are currently generated idempotently per `analysis_run_id`; existing
  schema prevents multiple cluster parameter variants for the same run because
  memberships are unique by `(analysis_run_id, message_pair_id)`.
- Existing cluster auto titles are placeholder labels (`Cluster N`) rather than LLM
  summaries.
- Existing embeddings are currently generated only for `message`; target state
  generates `message` and `answer` embeddings for every support pair.
- Cluster sources are already available through a project-scoped API but rendered
  inline, not in a dialog.
- Candidates are first-class in schema, service, API, UI and exports, but the user
  confirmed they are overflüssig in the new workflow; Cluster-Sets become the final
  analysis result.

## Impact matrix

| Layer or concern | Located artifact / current owner | Action | Required end state | Owning task | Verification evidence |
|---|---|---|---|---|---|
| UI and interaction state | Project tabs in `frontend/src/App.tsx` | replace | Tabs become Import, Indizieren, Cluster-Sets, Explorer and Projekt löschen; Profile, Kandidaten and separate Export removed | T1, T4 | UI tests + browser review |
| UI and interaction state | Project overview/sidebar | modify | Hauptpunkt Projekte zeigt Übersicht; geöffnete Projekte erscheinen als linke Unterpunkte | T4 | UI tests + browser review |
| UI and interaction state | Import overview | modify | Imports have editable display names and delete action with dependent-state markers | T2/T4 | API + UI tests |
| UI and interaction state | Indexing job cards | modify | Running jobs show percentage in status chip, progressbar, phase, cancel action and disabled cluster-set usage until finished | T2/T4 | API + UI tests |
| UI and interaction state | Cluster-set overview | replace | Saved sets render as expandable parent/child analysis tree with history and parent/child load actions | T3/T4 | UI tests + browser review |
| UI and interaction state | Cluster-set job cards | modify | Running cluster-set jobs show percentage in status chip, progressbar, phase, cancel action and disabled Explorer loading until finished | T3/T4 | API + UI tests |
| UI and interaction state | Settings provider tab | modify | Split or nested tabs for Embedding-Provider and LLM-Provider | T1, T2 | UI tests + visual evidence |
| UI and interaction state | Cluster Explorer cards and inline source list | replace | Dense table with grouped categories, lineage panel, text search, outlier/mismatch controls, exclusion controls and modal source dialog | T4 | component tests + browser review |
| UI and interaction state | Explorer export section | modify | Separate Explorer-level panel exports current search/filter table state as CSV or JSON; not in the tabular-analysis header; no separate Export tab | T4 | API + UI tests |
| Frontend validation and feature model | `AnalysisProfile`, `AnalysisRun`, `Cluster`, `Candidate` types | replace | `IndexingRun`, `ClusterSet`, `ClusterSummary`, `ClusterSourceDialog` models; no candidate model in primary workflow | T2-T5 | TypeScript build/tests |
| Public API or message contract | `/analysis-profiles` routes | remove | No active profile API in new workflow | T2 | API tests + orphan search |
| Public API or message contract | `/analysis-runs` routes | replace | Indexing routes or compatibility-free renamed routes | T2 | API contract tests |
| Public API or message contract | `/analysis-runs/{run_id}/clusters` | replace | Cluster-set routes keyed by indexing run and cluster set | T3 | API contract tests |
| Backend schema and application service | `ProviderService` owns provider config and profiles | replace | Provider config stays; profile persistence removed; LLM provider config introduced | T2 | provider tests |
| Backend schema and application service | `AnalysisService` | modify | Owns indexing run lifecycle, progress, cancellation and embeddings | T2 | service tests |
| Backend schema and application service | `ClusterService` | replace | Owns cluster-set generation, progress, cancellation, lineage/event history, source snapshots, summary generation, source filtering/refinement, outlier thresholds and mismatch indicators | T3 | service tests |
| Backend schema and application service | `CandidateService` | remove | Cluster-Sets replace candidates as final analysis artifacts | T5 | tests adjusted/removed |
| Persistence and migration | `analysis_profiles` table | remove | No active profile table unless retained only for destructive migration bridge | T2 | migration tests |
| Persistence and migration | `analysis_runs`, `embeddings` | migrate | `indexing_runs` and embeddings keyed to indexing run; no profile FK; two text variants per pair (`message`, `answer`) | T2 | migration/schema tests |
| Persistence and migration | `clusters`, `cluster_memberships` | migrate | `cluster_sets`, clusters and memberships keyed to cluster set; parent links, derivation type, source snapshots, events, deleted basis markers and outlier/mismatch metadata retained | T3 | migration/schema tests |
| Persistence and migration | `candidates`, `candidate_source_assignments` | remove | Candidate data may be dropped during local derived-data migration | T5 | migration tests |
| Integrations, jobs, events, caches, search | Embedding provider calls | modify | Invoked by indexing run for both message and answer embeddings with explicit model and preserved bounds | T2 | adapter tests |
| Integrations, jobs, events, caches, search | New LLM provider calls | modify | Bounded local/OpenAI LLM generation for cluster summaries using random per-cluster samples from 1 to all | T3 | stubbed adapter tests |
| Telemetry and operations | audit/status rows | modify | audit actions and queryable cluster-set events for indexing and cluster-set generation/refinement/exclusion/manual edits | T2-T4 | service/API tests |
| Backend domain errors | `ProviderError`, `AnalysisError`, `ClusterError`, `CandidateError` | replace | stable indexing/cluster-set/LLM errors with safe messages | T2-T4 | negative tests |
| Backend exception mapping | `backend/api/app.py` HTTPException mapping | modify | map new domain errors to safe API responses | T2-T4 | API tests |
| HTTP problem response | current free-form `detail` strings | modify | safe stable code/message contract if adopted by error policy | T2-T4 | API + UI tests |
| API contract | profile/run/cluster/candidate API models | replace | indexing/cluster-set/summary/source contracts; old candidate contract removed; Explorer filtered export endpoint added | T2-T5 | API tests |
| Error catalog | `docs/errors/ERROR_CATALOG.md` | modify | add new codes, remove obsolete profile/candidate codes if any | T6 | catalog checker |
| Generated client error types | not present; handwritten frontend API types | not-applicable | no generated client found | none | rg evidence |
| Frontend error normalization | `ApiRequestError` handling in `App.tsx` | modify | new actions preserve safe detail/fallback | T4 | frontend tests |
| Error-code mapping | currently mostly message-based | modify | code-aware mapping if cataloged API contract is introduced | T2-T4 | tests |
| Field error rendering | forms in `App.tsx` | modify | model/provider/parameter field errors preserve input | T4 | UI tests |
| Form-level error rendering | global feedback/status | modify | form-level safe errors for indexing and cluster-set generation | T4 | UI tests |
| Component-level error state | cluster set table/dialog | modify | row/dialog failures are visible and retryable | T4 | component tests |
| Page-level error state | project tab empty/error states | modify | explorer handles no set, failed set, no sources, excluded-only | T4 | UI tests |
| Toast or transient feedback | global feedback in `App.tsx` | modify | no false success; typed feedback remains | T4 | UI tests |
| Input preservation | current forms partial | modify | preserve selections/params/sample counts after provider/LLM/cluster failures | T4 | UI tests |
| Retry and recovery actions | limited current buttons | modify | retry summary, regenerate as new set, reload set, reopen dialog | T3-T4 | UI + API tests |
| Logging and correlation | audit/service diagnostics | modify | redacted diagnostics for LLM and cluster-set errors | T2-T3 | service tests |
| Negative-path tests | existing API/service/UI tests | modify | cover new failure matrix | T2-T5 | focused tests |
| Browser or visual error evidence | UI quality enabled | modify | revision-bound evidence after implementation | T4 | UI quality tools |
| Error-handling documentation | error catalog + spec | modify | current-state error behavior documented | T6 | check-user-facing-errors |
| Tests and fixtures | `tests/api`, `tests/db`, `tests/analysis`, `tests/clusters`, `tests/candidates`, `frontend/src/App.test.tsx` | replace | new indexing/cluster-set/LLM/explorer tests; obsolete profile/candidate tests removed | T2-T5 | focused + full verify |
| Documentation and specifications | MVP spec, local providers spec, ADR-0003, README/context | modify | current truth uses Indizierung, Cluster-Sets, LLM providers; ADR-0003 superseded | T6 | docs checker |

## New or parallel artifacts

| Proposed artifact | Existing responsibility searched | Why extension/replacement is insufficient | Compatibility need | Removal criterion |
|---|---|---|---|---|
| `indexing_runs` or renamed `analysis_runs` contract | `analysis_runs`, `AnalysisService` | current FK to profiles contradicts removed profiles and currently generates only message embeddings | no profile compatibility planned | no active profile FK; both text variants embedded |
| `cluster_sets` | `clusters`, `cluster_memberships` | current membership uniqueness by run prevents multiple saved parameter variants | none | cluster queries use set ID |
| LLM provider configuration | existing provider config only covers embedding use and profiles | LLM generation has separate model families, prompts, token limits, random sampling and cloud confirmation | can share secret/encryption utilities | settings expose separate LLM tab |
| Cluster source dialog component | inline source list | dialog is a distinct interaction with focus management and pagination/search needs | none | explorer sources no longer render as unfocused inline dump |

## Conditional impact annexes

## Component impact

### Existing components reused

- Existing sidebar/navigation shell.
- Existing tab button styling.
- Existing panel/form/button/status primitives in `frontend/src/App.tsx` and
  `frontend/src/App.css`.

### Existing components extended

- Project tab composition.
- Settings provider composition.
- Feedback/status presentation.

### New shared components

- Likely `DataTable` or feature-local cluster table after component reuse review.
- Likely `Dialog` if no existing accessible dialog primitive is present.

### New feature-local components

- Indexing form/list.
- Cluster-set generator/list.
- Cluster explorer table.
- Cluster source dialog.
- Refinement/exclusion controls.

### Components replaced or removed

- Analysis profile form/list.
- Run monitor naming and profile selector.
- Cluster card explorer.
- Project tab „Kandidaten“.
- Candidate service/API/schema unless retained only for a separately accepted export
  replacement.

### Rejected reuse options

- Existing `user-card` card list for cluster exploration: rejected because it does
  not support dense comparison, grouping, sorting or scan-friendly analyst work.

### Rationale

The requested analyst workflow requires a table-first information architecture and
focused detail drilldown rather than expanding card lists.

## Superseded artifacts

| Artifact | Disposition: remove/deprecate/replace/retain | Reason if retained | Owning task | Removal criterion or evidence |
|---|---|---|---|---|
| `analysis_profiles` table | remove/migrate | none if owner confirms destructive derived-data migration | T2 | migration tests |
| `/api/projects/{project_id}/analysis-profiles` | remove | no compatibility requested | T2 | route orphan search |
| Project tab „Profile“ | remove | no compatibility requested | T4 | UI tests |
| `AnalysisProfile*` frontend/backend types | remove | no compatibility requested | T2/T4 | type/build checks |
| ADR-0003 current decision | replace/supersede | historical record retained as superseded ADR | T6 | new ADR accepted |
| run-bound cluster generation | replace | cannot represent multiple cluster sets | T3 | cluster set tests |
| Project tab „Kandidaten“ | remove | user confirmed candidates are überflüssig in the new workflow | T5 | UI test |
| Project tab „Export“ | remove | export belongs to Explorer and uses the current search/filter table state | T5 | UI test |
| Candidate persistence/API/export | remove/replace | Cluster-Set is the final result; filtered Explorer export replaces old candidate export | T5 | migration/API/export tests |

## Concept-trace completion

- Repository-wide search terms and symbols:
  `AnalysisProfile`, `analysis_profiles`, `analysis-runs`, `AnalysisRun`,
  `embeddings`, `message`, `answer`, `clusters`, `cluster_memberships`,
  `Candidate`, `Kandidaten`,
  `provider`, `OpenAI`, `Ollama`, `vLLM`.
- Generated sources traced to their authoritative input: not-applicable; frontend
  types are handwritten.
- No relevant references remain unclassified: yes
- Uncertainty or intentionally excluded areas:
  low-level route names, SQL shape and exact LLM provider schema remain
  implementation details inside the accepted behavior.

## Acceptance

- Impact analysis complete: yes
- Accepted by: anfordernder Product Owner
- Date: 2026-08-04
