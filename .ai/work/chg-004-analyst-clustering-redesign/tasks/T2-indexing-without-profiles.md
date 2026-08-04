# Task T2: Indizierung ohne Analyseprofile

- Status: verified
- Parent requirement or change: `docs/requirements/chg-004-analyst-clustering-redesign.md`
- Plan: `.ai/work/chg-004-analyst-clustering-redesign/PLAN.md`
- Work type: incremental-change
- Review batch: per-task
- Depends on: accepted CHG-004, approved design, canonical specs, ADR-0007
- Owner/agent: implementer
- Last updated: 2026-08-04

## Objective

Replace the active profile/run embedding flow with Indizierungen: profile-free
dataset/model selection, indexing job lifecycle, both `message` and `answer`
embeddings, progress/cancel/delete semantics and safe migration.

## Scope

### In scope

- Replace profile/run embedding flow with profile-free indexing contract, persistence, migration and UI.
- Persist `message` and `answer` embeddings per valid pair while preserving existing chunking, batching, pooling, validation and provider safety.
- Add indexing progress percentage, phase, cancellation, safe errors, import display names/deletion, deleted-dataset marker and indexing deletion.
- Add migration, API/service and focused UI tests.

### Out of scope

- Cluster-Sets, LLM providers, Explorer/export, and final candidate removal unless a migration dependency requires a transitional decision.
- Production data or production environment access.

## Preconditions

- Canonical specs are updated; ADR-0007 is accepted; ADR-0003 is superseded; prototype remains isolated.

## Impact and responsibility

- `IMPACT.md` rows closed: profile API removal; indexing route/contract replacement; embedding schema migration; indexing errors; initial Profile/Runs UI removal; import/indexing display-name/delete semantics.
- Existing responsibility extended/replaced/deprecated/removed: `AnalysisService`, `/analysis-runs`, `/analysis-profiles`, profile-owned provider behavior, frontend profile/run state.
- New or parallel artifacts and accepted justification: indexing contract replaces run/profile contract because profiles are removed without compatibility.
- Superseded artifacts assigned to this task: active profile form/routes/types; profile FK for indexing; message-only embedding generation.

## Affected files or components

- Backend/API/migrations: `backend/api/app.py`, `backend/analysis/service.py`, `backend/providers/service.py`, `backend/db/migrations/`
- Frontend/tests: `frontend/src/App.tsx`, `frontend/src/App.css`, `tests/api`, `tests/analysis`, `tests/db`, `tests/providers`, frontend tests

## Acceptance criteria

- [x] Profile-free Indizierung starts from dataset/provider/model and persists `message` plus `answer` embeddings per valid pair.
- [x] Running jobs show percentage, progressbar, phase and cancel action; non-finished jobs cannot be selected for clustering.
- [x] Import/indexing rename/delete semantics and deleted-source markers work.
- [x] Active Profile/Runs dependencies are removed/replaced and focused backend, migration and UI tests pass.

## Security Assurance

- Security assurance: required
- Security triggers: sensitive support text, OpenAI transfer, provider secrets, local network endpoints, public API change, migration, deletion.
- Assets and data classes: support texts, embeddings, OpenAI keys, local endpoints, project/user/session data, import/indexing metadata.
- Trust boundaries and untrusted inputs: browser requests; imported text; provider responses; local provider URLs; database migration state.
- Authorization model: authenticated user plus server-side project scoping on every route.
- Threats and abuse cases: cross-project access; cloud submission without confirmation; secret/raw-text disclosure; SSRF through endpoint; unbounded provider/resource use; migration data loss beyond accepted scope; false success after cancel/delete failure.
- Mitigations: project-scoped queries; OpenAI confirmation; write-only secrets; redacted diagnostics; local endpoint allow-list; chunk/batch/pooling bounds; migration tests; safe idempotent cancel/delete handling.
- Security verification: auth/project-isolation tests, endpoint rejection tests, OpenAI confirmation tests, migration tests, safe-error negative tests, `./.ai/tools/security.sh`.
- Residual security risk: accepted destructive local derived-data migration; local backup note is documented before migration use.
- Specialist security review: required for migration, public API, secrets and sensitive text processing.

## Error and recovery implementation

### User actions covered

- Load: indexing list, import overview.
- Create/update/delete/background: start Indizierung; autosave display names where implemented; delete import; delete/cancel Indizierung; OpenAI cloud confirmation.
- Search/export/download: not-applicable.
- Import/upload: import deletion state only; parser/upload unchanged unless touched.

### Expected failures

| Error code | Trigger | Backend mapping | UI placement | User message | Recovery |
|---|---|---|---|---|---|
| `INDEXING_MODEL_UNAVAILABLE` | embedding model missing | domain error to safe API problem | Indizierungsformular | Das gewählte Embedding-Modell ist nicht verfügbar. Bitte Provider-Einstellungen prüfen oder ein anderes Modell wählen. | provider prüfen or model wechseln |
| `INDEXING_CLOUD_CONFIRMATION_REQUIRED` | OpenAI indexing without confirmation | validation/business-rule problem | Indizierungsformular | Diese Indizierung würde Originaltexte an OpenAI senden. Bitte Cloud-Nutzung bewusst bestätigen. | confirm or choose local model |
| `INDEXING_CANCEL_NOT_AVAILABLE` | terminal/non-cancellable job | conflict/business-rule problem | indexing card | Diese Indizierung kann nicht mehr abgebrochen werden, weil sie bereits fertig, fehlgeschlagen oder abgebrochen ist. | refresh list |
| `IMPORT_IN_USE_DELETED` | import deletion affects existing indexing | confirmation/success warning | Importübersicht | Der Datensatz wird gelöscht; bestehende Indizierungen und Cluster-Sets bleiben erhalten und zeigen die gelöschte Quelle. | confirm or cancel |
| `INDEXING_RUN_DELETED` | indexing deletion affects later cluster sets | confirmation/success warning | Indizierungsübersicht | Die Indizierung wird gelöscht; bestehende Cluster-Sets bleiben erhalten und zeigen die gelöschte Basis. | confirm or cancel |

### Unknown failure behavior

- User-facing fallback: Die Aktion konnte nicht abgeschlossen werden. Bitte erneut versuchen.
- Correlation ID: safe request/job identifier when available.
- Retry behavior: retry unless the action already reached a terminal state.
- Input preservation: preserve selected dataset/provider/model and typed names.
- Support behavior: no secrets, raw support text, SQL, stack traces, paths or provider bodies in UI.

### Required negative tests

- [x] Required: validation, authentication, authorization, not-found, conflict, business-rule, dependency unavailable, network, timeout and cancellation.
- [x] Required: unexpected server error, unknown code, failed optimistic update and no false success feedback.

### Error acceptance criteria

- [x] Changed actions handle failure; known failures use catalogued codes; unknown failures use safe fallback; failed writes preserve safe input; backend/client/frontend mappings agree; raw technical details are not displayed.

## UI classification

- Design class: 3
- Prototype strategy: isolated-prototype
- Visual review required: yes

## Component impact

### Existing components reused

- Existing sidebar, tabs, forms, cards, buttons and status primitives.

### Existing components extended

- Project tabs, provider/model selectors and feedback/status presentation.

### New shared components

- None.

### New feature-local components

- Indizierung form/list state.

### Components replaced or removed

- Profile form/list and Runs tab naming/profile selector.

### Rejected reuse options

- Reusing profile form state: rejected because it keeps removed fields.

### Rationale

- Starts the accepted IA while limiting UI work to indexing.

## Prototype relationship

- Prototype: `.ai/work/chg-004-analyst-clustering-redesign/prototype/index.html`; promote labels/structure only; discard fake data/mock text/static code; no tool dependencies.

## Visual evidence

- Required screens: Project → Import and Indizieren.
- Required states: empty, running, completed, failed, cancelled, deleted dataset, OpenAI confirmation, error/failure.
- Required viewports: desktop 1440x1000 and mobile 390x844.
- T2 decision: deferred to T4/T6 visual review because the active implementation-phase gate does not require browser evidence before this slice is verified.
- Manifest: `.ai/work/chg-004-analyst-clustering-redesign/evidence/ui/T2-ui-evidence-decision.md`.

## Implementation constraints

- Do not depend on the prototype.
- Do not add profile compatibility.
- Preserve provider safety bounds, project isolation and production-access prohibition.

## Applicable capability specification and test seam

- Specification criteria: `docs/specifications/support-knowledge-miner-mvp1.md` AC-6 through AC-9 and FR-12 through FR-27.
- Primary observable boundary for this task: backend API/service plus frontend indexing workflow.
- Implementation-specific boundaries to avoid testing directly: private helpers and exact React internal state.

## Verification

- [x] Focused tests
- [x] Relevant linting/static analysis
- [x] Security or dependency checks when applicable
- [x] Documentation assessment, including `README.md` and `.ai/PROJECT_CONTEXT.md`

Exact commands: `UV_PYTHON=3.13 uv run --locked python -m pytest tests/analysis/test_analysis_service.py tests/api/test_analysis_run_api_integration.py tests/clusters/test_cluster_service.py -q`, `(cd frontend && npm run test -- --run)`, `./.ai/tools/format.sh --check`, `./.ai/tools/lint.sh`, `./.ai/tools/test.sh`, `./.ai/tools/security.sh`, `./.ai/tools/build.sh`, `./.ai/tools/check-dependencies.sh`, `./.ai/tools/ui-quality.sh accessibility`, `./.ai/tools/verify.sh`.

## Risks or blockers
No active blocker. Destructive local migration has a local backup note in `deployment/docker/README.md`; old cluster/candidate dependencies are handled by the accepted T2 transitional bridge and later T3/T5 tasks.

## Result

Implemented the profile-free indexing slice:

- Backend `AnalysisService` now starts indexing from dataset/provider/model,
  rejects legacy profile/run-mode parameters, persists `message` and `answer`
  embeddings, and exposes cancel/delete/list/detail/embedding APIs with safe
  problem responses.
- Migration 0014 removes active analysis-profile schema, resets accepted
  derived local data, preserves imports/projects/providers, and adds indexing
  lifecycle/deletion columns.
- Frontend removes the Profile tab and legacy Runs workflow, adds the
  Indizieren form/list with progressbar, phase, OpenAI confirmation,
  cancel/delete, and active/deleted dataset markers.
- Import dataset display-name and soft-delete semantics are wired through API,
  service, UI and tests.
- Smoke scripts, migration assertions, MVP/project docs and frontend/backend
  tests were updated for the new contract.
- Dependency gates required updating `cryptography` to 50.0.0 and refreshing
  audited frontend transitive dependencies; `.gitleaksignore` now baselines
  three historical non-secret false-positive fingerprints without disabling new
  secret findings.
- Review remediation closed the remaining T2 risks: catalog-aligned problem
  details, code-aware frontend safe-error mapping, no arbitrary Indexing-Run
  parameters, late-cancel finalization, destructive delete confirmations,
  operator backup note, dependency review evidence and pre-review status.

Dependency review evidence:

- Python: `cryptography` was raised to `>=50,<51` and locked at `50.0.0` to
  resolve `pip-audit` findings without introducing a new runtime dependency.
  Provider secret storage paths remain covered by tests and `bandit`/`gitleaks`.
- Frontend: `npm audit fix` refreshed vulnerable transitive packages in
  `frontend/package-lock.json`; direct frontend dependency choices did not
  change.
- Verification: `./.ai/tools/check-dependencies.sh` passed with lockfile and
  vulnerability scans.

Observed verification:

- `./.ai/tools/format.sh --check` passed.
- `./.ai/tools/lint.sh` passed.
- `./.ai/tools/test.sh` passed: 170 backend tests, 36 frontend tests, 5 Bats tests.
- `./.ai/tools/security.sh` passed.
- `./.ai/tools/build.sh` passed.
- `./.ai/tools/check-dependencies.sh` passed.
- Focused remediation subset passed: 40 backend tests.
- Frontend `npm run test -- --run` passed: 36 tests.
- `./.ai/tools/ui-quality.sh accessibility` passed after the primary button
  contrast adjustment.
- Final `./.ai/tools/verify.sh` passed: 170 backend tests, 36 frontend tests,
  5 Bats tests; documentation warnings only for context budget.

### Adversarial pre-review

- Adversarial pre-review: passed
- Pre-review lenses: public API/problem details, user-facing errors, UI destructive actions, migration/operator safety, dependency evidence, cancel lifecycle, transitional cluster compatibility, artifacts.
- Pre-review evidence: implementation diff, focused remediation tests, frontend safe-error/delete-confirmation tests, `./.ai/tools/verify.sh`, `./.ai/tools/ui-quality.sh accessibility`, T2 UI-evidence decision.
- Open P0/P1 findings: none
- Findings remediated:
  - Problem responses now use `urn:skm:error:*`, catalog titles/details/actions
    and 422/409 statuses for known Indexing errors.
  - Frontend maps known problem codes to safe German messages and maps unknown
    codes to a generic fallback instead of rendering backend details.
  - The Indexing API rejects any submitted `parameters`; service persists empty
    Indexing parameters and transitional clustering ignores old
    `algorithm_settings`.
  - Late cancellation after the last cooperative check finalizes as `cancelled`.
  - Dataset and Indexing delete actions require explicit browser confirmation.
  - `deployment/docker/README.md` documents the local backup requirement before
    the destructive 0014 migration.
  - Dependency remediation and UI-evidence deferral are recorded.
- P0/P1 status before final reviewer verification: no known open P0/P1.

### Independent review

- Reviewer: Ptolemy (`019fcd54-bbf5-75b2-ae1b-87da8e38161a`)
- Result: review-acceptable
- P0/P1/P2 findings: none
- P3 findings:
  - Parent plan still marked T2 in progress: fixed in `PLAN.md`.
  - Deprecated `parameters` request field remains to preserve catalogued legacy
    problem-response handling; cleanup deferred until that compatibility signal
    is no longer needed.
  - Queue overload currently uses `UNEXPECTED_ERROR` with HTTP 503; a dedicated
    capacity/dependency error code is deferred to a future contract-tightening
    cleanup.
