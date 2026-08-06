# Implementation plan: Provider-Einstellungen zentralisieren

- Status: ready
- Change class: significant
- Work type: incremental-change
- Requirement: current user request from 2026-08-05
- Change request: `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/CHANGE.md`
- Change impact: `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/IMPACT.md`
- Design delta: `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/DESIGN_DELTA.md`
- Canonical capability specifications:
  `docs/specifications/local-runtime-providers.md`,
  `docs/specifications/support-knowledge-miner-mvp1.md`
- Work directory: `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/`
- Last updated: 2026-08-06

## Outcome and implementation boundary

- In scope: Implement the approved provider settings centralization, active vLLM
  removal, provider-instance migration/provenance, feedback overlay, Import/Explorer
  adjustments, optional indexing provider-input line-break/lowercase normalization,
  explicit provider connection tests, separate available-model state, and removal of
  the previously planned global indexing/Cluster-Set start guards.
- Non-goals: Prozentgenauer Ollama-Downloadfortschritt, vLLM-Reintegration,
  OpenAI-Cloud-confirmation changes and any production/remote-environment access.
- Accepted assumptions: Provider display names are user-controlled and may be
  duplicate; provider instance ID is the technical identity. Provider deletion is
  hard deletion from active configuration while historical provenance snapshots
  remain readable. Ollama pull only needs running/final-success/final-failure status.
- Open blockers: none.

## Current-state findings and approach

- Existing provider settings are owned by `frontend/src/App.tsx`,
  `backend/providers/service.py`, `backend/api/app.py`, and
  `provider_configurations`.
- Existing jobs are owned by `backend/analysis/service.py` and
  `backend/clusters/service.py`; each already has bounded local queues, two daemon
  workers and cancellable statuses. The planned global start guards are no longer
  the desired state and are removed so bounded parallel execution is available.
- Current provider state conflates available models and selected/freigegebene
  models. The implementation separates `available_models` from the Embedding and
  LLM allow-lists so checkbox ordering is stable and unselected models remain
  visible until a successful discovery removes them.
- Existing import logs already expose `started_at`/`completed_at` backend-side; the
  frontend ignores the fields.
- Existing cluster sets have `updated_at`; Explorer needs to choose the last updated
  completed set, and Explorer edits must update the owning Cluster-Set timestamp.
- Existing indexing runs already persist `parameters`; the line-break/lowercase
  normalization option can use that JSONB provenance without a new migration, while
  embeddings record active normalization in metadata.
- Implementation extends existing responsibilities instead of adding parallel
  provider/job systems.

## Affected areas

- UI and interaction state: Settings tabs/cards, feedback overlay, Indizieren,
  Cluster-Sets, Import and Explorer.
- API contracts: Provider instance CRUD/check/pull, job activity status, indexing and
  Cluster-Set creation payloads/responses.
- Data and migrations: Provider instance IDs, display-name, available models,
  purpose-specific model allow-lists, provenance snapshots and active vLLM removal.
- Services/jobs: Provider runtime validation, connection test/discovery, Ollama pull
  guard, bounded parallel indexing/Cluster-Set execution.
- Tests/docs/errors: Service/API/frontend tests, migration tests, capability specs,
  design docs and error catalog.

## Conditional plan annexes

## UI classification

- Design class: 3
- Highest design class assigned: 3
- Implementation-start design class: 3
- Prototype strategy: isolated-prototype
- Prototype artifact/revision:
  `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/prototype/settings-provider-centralization-mockup.html`;
  `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/prototype/project-workflow-adjustments-mockup.html`;
  `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/prototype/cluster-summary-explorer-optimization-mockup.html`
- Design approval status: approved by Product Owner on 2026-08-05.
- Visual review required: yes after production implementation; evidence must cover
  desktop and mobile Settings, feedback overlay, Import protocol, Explorer empty and
  loaded states, and bounded queued/running job states without global start
  blocking.
- Existing components reused: App shell, tabs, cards/panels, feedback status styles,
  checkbox groups, form rows.
- Existing components extended: Provider forms, feedback message, project workflow
  forms, Explorer/export composition, app topbar/navigation and Cluster-Set cards.
- New shared components: none planned; feature-local helpers in `App.tsx` are allowed
  because the app shell is currently monolithic.

## Error handling

## Error-handling strategy

### Actions covered

Provider create/update/delete/check, Ollama model pull, indexing start,
Cluster-Set start/refine/recalculate, Explorer default loading, import log details
visibility and global feedback display.

### Error contract changes

New or newly active codes: `VALIDATION_FAILED`,
`PROVIDER_MODEL_PULL_IN_PROGRESS`, `PROVIDER_DELETE_FAILED`,
`PROVIDER_DELETE_BLOCKED`. Existing provider/model/cloud-confirmation codes remain
active. The previously planned `INDEXING_ALREADY_RUNNING` and
`CLUSTER_SET_ALREADY_RUNNING` start guards are superseded and removed from active
behavior.

### Error catalog changes

`docs/errors/ERROR_CATALOG.md` and `docs/api/problem-details-contract.yaml` are
updated for the new Provider contracts and removal of active global job-guard
codes.

### Frontend normalization changes

`frontend/src/App.tsx` maps all new active codes through the central
`ERROR_MESSAGES_BY_CODE` normalizer and keeps the existing unknown-code fallback.

### Presentation components

Primary failures appear in the affected form/card/table area where available and
also use the global feedback overlay. The overlay has a manual close button and
auto-dismiss.

### Input preservation

Provider cards preserve safe non-secret fields, available model ordering and
selected model allow-lists; OpenAI API keys are never echoed. Indexing and
Cluster-Set forms preserve selected dataset/provider/model/parameters on validation
or queue failures. Ollama pull input is preserved on blocked or failed requests
where safe.

### Retry and recovery

Validation failures are retryable after correction. Queue-capacity failures are
retryable later. Provider deletion failures ask for reload/retry. Ollama
pull-in-progress asks the user to wait.

### Logging and correlation

Backend Problem Details and audit paths use safe request/job/provider references
only. Provider diagnostics are redacted and must not include secrets, raw provider
bodies, raw support text, SQL, stack traces or local credentials.

### Negative-test strategy

Service/API/frontend tests cover vLLM rejection, provider validation/delete/pull
errors, provider connection tests, model discovery reconciliation, parallel
indexing/Cluster-Set starts, import details visibility, Explorer default loading and
safe feedback.

### Visual error-state verification

UI evidence must include Provider/Ollama failure or blocked state, feedback overlay,
and bounded queued/running job states in desktop/mobile browser review.

### Removed or superseded error behavior

The old separate Embedding-/LLM-Provider tab errors and visible vLLM active paths
are superseded. Free-text OpenAI LLM model validation is removed with the field.

## Security Assurance routing

- Security assurance: required
- Security triggers: secrets, local-network endpoints, public API contract changes, migration,
  hard delete, external provider calls, long-running/cancellable jobs.
- Assets and data classes: encrypted OpenAI API key secret references, provider endpoint
  URLs, imported support text provenance, analysis/cluster job metadata, audit logs.
- Trust boundaries and untrusted inputs: browser payloads, provider endpoint/model names,
  Ollama/OpenAI responses, database state after migration.
- Authorization model: existing authenticated API boundary; project-scoped actions
  continue to validate project membership through current services.
- Threats and abuse cases: secret disclosure through placeholder/API/errors, non-local
  provider endpoint misuse, duplicate display-name ambiguity, hard deletion erasing
  provenance, unbounded parallel job resource exhaustion, unsafe provider failure
  details.
- Mitigations: write-only secret behavior, endpoint allow-listing, stable provider
  instance IDs, provenance snapshots, bounded worker queues/resource budgets,
  redacted Problem Details, parameterized SQL, bounded provider requests.
- Threat model: Browser payloads, migrated database rows and provider responses are
  untrusted; the API preserves project scope, secret redaction, local endpoint
  allow-listing and global resource guards before any provider call or job start.
- Security verification: provider/API/migration/analysis/cluster negative tests,
  user-facing error gate, security gate and repository search for removed active
  vLLM paths.
- Residual security risk: vLLM may appear only in historical/superseded documents or
  provenance strings; no active UI/API/runtime path accepts it for new execution.
- Specialist security review: required for the migration/API/provider-runtime task
  because secrets, network and irreversible deletion are involved.

## Review cadence

- Cadence: per-task
- Rationale: migration, public API, security-sensitive provider handling and UI
  behavior changes trigger per-task review under project policy.

## Work items

| ID | Vertical outcome | Status | Depends on | Review batch | Impact rows closed | Task file |
|---|---|---|---|---|---|---|
| T001 | Static settings and project workflow mockups plus assessment | verified | none | RB001 | UI draft and temporary artifact rows | `tasks/T001-settings-provider-mockup.md` |
| T002 | Provider-instance schema/API/runtime with vLLM removed from active support | in-progress | T001 | RB002 | Provider persistence, API, service, provenance, active vLLM removal | `tasks/T002-provider-instances-api-runtime.md` |
| T003 | Analysis and Cluster-Set flows use provider instance IDs, optional indexing input normalization and bounded parallel starts | ready | T002 | RB003 | Domain selection, input normalization, bounded concurrency, cancellation compatibility | `tasks/T003-provider-jobs-analysis-clusters.md` |
| T004 | Frontend implements approved Provider tab, feedback overlay and project workflow adjustments | ready | T002,T003 | RB004 | Settings UI, Import, Explorer, provider test/discovery states | `tasks/T004-frontend-provider-project-ui.md` |
| T005 | Specs, design docs, error catalog and full verification evidence | ready | T002,T003,T004 | RB005 | Documentation/error/design/current-state closeout prep | `tasks/T005-docs-verification-review.md` |
| T006 | Cluster-Summary-Neuerstellung und HDBSCAN PCA/UMAP/cuML runtime parameters | verified | T003,T004 | RB006 | Cluster-Set summary retry, LLM diagnostics, HDBSCAN progress/runtime settings | `tasks/T006-cluster-summary-and-hdbscan-variants.md` |
| T007 | Optional RAPIDS/cuML dependency extras | verified | T006 | RB007 | Optional GPU dependency packaging and install documentation | `tasks/T007-optional-rapids-cuml-dependency.md` |
| T008 | Explorer-Arbeitsfläche mit linker Kontrollleiste, globalem Menübutton und Summary-Neuerstellung | in-progress | T004,T006 | RB008 | Explorer IA/navigation, Explorer export/filter/outlier controls, Summary action placement, Cluster-Set summary dialog | `tasks/T008-explorer-control-rail-global-menu-summary-dialog.md` |

## Acceptance-criteria traceability

| Criterion | Work item | Verification |
|---|---|---|
| AC-1..AC-8 mockup and assessment | T001 | `git diff --check`, screenshot rendering |
| AC-9 Provider/Nutzer Settings UI and CRUD | T002,T004 | API/service/frontend tests and browser evidence |
| AC-10 provider instance migration/provenance | T002,T003 | migration/service/API tests |
| AC-11 active vLLM removal | T002,T004 | repository search and negative tests |
| AC-12 Ollama pull status/guard | T002,T004 | provider API/frontend tests |
| AC-13 Import/Explorer behavior | T003,T004 | frontend/API/service tests |
| AC-14 bounded parallel job starts | T003,T004 | service/API/frontend tests |
| AC-15 Optional line-break/lowercase normalization for indexing provider input | T003,T004 | `PYTHONPATH=. uv run --locked pytest tests/analysis/test_analysis_service.py tests/api/test_analysis_run_api_integration.py`; `npm test -- --run src/App.test.tsx` |
| AC-16 Explorer uses a left control rail for cluster-set selection, search/filter, outlier controls, Summary regeneration and export | T008 | frontend tests, desktop/mobile browser evidence, accessibility review |
| AC-17 Global app navigation is opened from a top-right menu button replacing the visible Abmelden button location; overlay entries are Projekte, Einstellungen and Abmelden | T008 | frontend navigation/menu tests, keyboard/focus tests, browser evidence |
| AC-18 Cluster-Sets keep Summary regeneration as Option A dialog; Explorer also exposes Summary regeneration in the left control rail | T008 | frontend tests, API contract compatibility checks, browser evidence |
| AC-19 Summary regeneration mode is planned with explicit write behavior: replace current summaries first, and optionally save a Summary version or Cluster-Set copy only after accepted backend semantics | T008 | service/API/frontend tests if optional modes are implemented; otherwise documented disabled/future state |

## Superseded-artifact and canonical-spec closeout

- Superseded active UI: Settings tabs `Embedding-Provider` and `LLM-Provider`,
  visible vLLM card/options, free-text OpenAI/Ollama LLM model fields, right-side
  Explorer export panel, visible global sidebar in signed-in workspaces, standalone
  visible `Abmelden` topbar button.
- Superseded active backend behavior: provider configuration keyed only by provider
  type; active vLLM provider validation/runtime paths.
- Capability specifications to update in place:
  `docs/specifications/local-runtime-providers.md`,
  `docs/specifications/support-knowledge-miner-mvp1.md`.
- Design docs to update after implementation:
  `docs/design/DESIGN_SYSTEM.md`,
  `docs/design/COMPONENT_CATALOG.md`.
- Temporary prototypes/evidence disposition: keep until visual/code review, then
  delete or explicitly retain as permanent design references during closeout.

## Verification and closeout

- Focused backend checks: targeted pytest files for providers, analysis, clusters,
  API and migrations.
- Focused frontend checks: `npm test -- --run` or affected App tests, `npm run build`
  as needed.
- Static checks: `git diff --check`, error catalog check, UI quality check.
- Full command before handoff: `./.ai/tools/verify.sh`.
- Independent reviews: code/security review and visual review required before tasks
  complete.

## Material deviations

- 2026-08-05: Added accepted user-requested indexing option for line-break
  removal/replacement as provider-input normalization. No migration required because
  normalized parameters fit existing `analysis_runs.parameters`; original support
  texts remain unchanged.
- 2026-08-05: Follow-up diagnosis showed `bge-m3:latest` still returns NaN for
  some normal mixed-case chunks after line-break normalization. Added optional
  provider-input lowercasing to the same normalization block.
- 2026-08-05: Follow-up optimization request superseded purpose checkboxes and
  global single-job guards. Provider usage is now derived from selected
  Embedding/LLM model allow-lists, available models are stored separately from
  selected models, and indexing/Cluster-Set/outlier starts are allowed in bounded
  parallel worker queues.
- 2026-08-06: Follow-up planning-only UI direction added `T008`: Explorer gets a
  left control rail for selection, search/filter, outlier controls, Summary
  regeneration and export; global navigation moves behind a top-right menu button
  whose overlay contains Projekte, Einstellungen and Abmelden; Cluster-Sets keep
  Summary regeneration as Option A dialog. No production implementation was
  authorized in this planning step.
- 2026-08-06: Product Owner released `T008` for future implementation after
  planning. Implementation was explicitly not started in this turn.
- 2026-08-06: T007 independent read-only dependency/security review completed with
  no open P0/P1 findings. Mechanical review closeout reconciled T007 status,
  current-plan pointer, T008 work-state formatting and generic CUDA README wording.
  T007 remains `verified` because CHG-005 is Design Class 3 and the UI-quality gate
  blocks `reviewed`/`done` task statuses until the approved visual-review phase.
- 2026-08-06: Implemented `T008` production UI: Explorer left control rail, top-right
  global menu overlay, Summary replacement dialog, Explorer Summary rail action and
  moved export controls. Focused frontend tests, format, lint/typecheck and frontend
  build passed; full `./.ai/tools/verify.sh` passed. Browser/accessibility/visual
  evidence remains pending before UI-quality review.
