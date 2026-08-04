# Plan: Analystenorientierte Indizierungs- und Clusteranalyse

- Change ID: CHG-004
- Status: implementation
- Classification: significant
- Rationale: ersetzt zentrale Domänenkonzepte, Persistenz, API-Verträge,
  Providerkonfiguration, UI-Informationsarchitektur und Hauptanalyseworkflow.
- Requirement: `docs/requirements/chg-004-analyst-clustering-redesign.md`
- Change request: `.ai/work/chg-004-analyst-clustering-redesign/CHANGE.md`
- Impact: `.ai/work/chg-004-analyst-clustering-redesign/IMPACT.md`
- Proposed spec: `.ai/work/chg-004-analyst-clustering-redesign/PROPOSED_SPEC.md`
- Design delta: `.ai/work/chg-004-analyst-clustering-redesign/DESIGN_DELTA.md`
- Mockup: `.ai/work/chg-004-analyst-clustering-redesign/prototype/index.html`
- Cadence: per-task
- Last updated: 2026-08-04

## Current phase

T2 is verified and independently review-acceptable. Profile-free indexing,
destructive local derived-data migration, UI workflow, remediation and full local
verification are complete. Next implementation work is T3 Cluster-Sets and LLM
summaries; final design-class-3 visual completion remains deferred to the later
UI slices.

## Routing

- Incremental change workflow: required.
- UI quality: required, design class 3.
- Error handling: required because user-triggered actions change.
- Security assurance: required
- Security triggers: imported support texts, OpenAI transfer, secrets, local network
  providers, migrations, public API changes and deletion of derived local data.
- Threat model: captured in each ready work item Security Assurance section; T2
  uses `tasks/T2-indexing-without-profiles.md`.
- Specialist security review: required per task for migration, public API, secrets,
  provider-safety and sensitive-text processing scope.
- Dependency review: not required unless implementation adds or changes manifests
  or lockfiles.
- Documentation review: required.

## Implementation sequence

### T1 — Accepted design and contract cleanup — completed

- Finalize decisions from `DISCOVERY.md`.
- Approve `DESIGN_DELTA.md`.
- Update canonical specs and supersede ADR-0003.
- Finalize error catalog plan.

### T2 — Indizierung without profiles — verified

- Work item: `.ai/work/chg-004-analyst-clustering-redesign/tasks/T2-indexing-without-profiles.md`

- Remove analysis profile creation/start dependency.
- Introduce indexing run contract and persistence.
- Generate both `message` and `answer` embeddings for every support pair.
- Add import display names, import deletion, deleted-dataset markers and indexing
  deletion semantics.
- Add indexing job progress with percentage, phases, cancellation and disabled
  cluster-set usage until completed.
- Keep embedding bounds, progress, provider safety and project isolation.
- Add migration and regression tests.

Non-blocking cleanup noted by independent review: remove the deprecated
`parameters` request field when legacy problem-response compatibility is no
longer needed, and consider a dedicated capacity/dependency error code for local
indexing queue overload.

### T3 — Cluster-Sets and LLM summaries

- Add cluster-set persistence and multiple saved sets per indexing run.
- Add vector-basis selection from indexed `message`, `answer` or combined Q/A pair
  vectors with persisted weighting.
- Move algorithm parameters to cluster-set creation.
- Add LLM provider config and bounded optional summary generation.
- Add random per-cluster LLM example sampling from 1 to all with persisted
  strategy/seed.
- Add source filtering for refinement, including second-stage clustering with a
  different vector basis than the parent Cluster-Set.
- Add cluster-set lineage: parent links, derivation type, source snapshots and
  event history for structural and non-structural edits.
- Add cluster-set job progress with percentage, phases, cancellation and disabled
  Explorer loading until completed.
- Add cluster-set display names, delete semantics and deleted-indexing markers.
- Add outlier threshold parameters and question/answer mismatch metadata.

### T4 — Explorer UI

- Replace Profile/Runs/Kandidaten navigation with Indizieren, Cluster-Sets,
  Explorer.
- Add project overview and nested project navigation.
- Implement table-first explorer.
- Implement cluster-set tree, parent/child navigation and Explorer analysis path.
- Implement text search, outlier controls and mismatch indicators.
- Implement separate Explorer export section for CSV/JSON export of the current
  filtered table state.
- Implement source dialog.
- Implement exclusion/include and refinement controls.
- Add UI tests and browser evidence.

### T5 — Remove candidates and obsolete export tab

- Remove candidate UI/API/schema/export paths made obsolete by Cluster-Sets as final
  analysis artifact.
- Remove the separate project Export tab; Explorer owns filtered CSV/JSON export.

### T6 — Verification, review, closeout

- Run focused backend/frontend/migration/security checks during work.
- Finish with `./.ai/tools/verify.sh`.
- Independent code and visual review.
- Update maintained docs and reset temporary work after acceptance.

## Review cadence

Per-task for migration/public API/security-sensitive slices. UI implementation may
use small review batches only after the accepted design artifact exists.

## Error-handling strategy

### Actions covered

CHG-004 covers project/import/indexing/cluster-set/explorer/export actions listed
in `CHANGE.md`; T2 implements the indexing subset first.

### Error contract changes

New known failures use stable codes from the `CHANGE.md` Error-and-Recovery Matrix.
Unexpected failures use `UNEXPECTED_ERROR`.

### Error catalog changes

`docs/errors/ERROR_CATALOG.md` declares CHG-004 codes. Implementation tasks replace
planned mappings with concrete backend/frontend owners as code lands.

### Frontend normalization changes

Use the existing central API error normalization path; add code-aware handling only
there.

### Presentation components

Form/card/dialog/table failures render in-place with `role="alert"`; non-error
feedback uses `role="status"`.

### Input preservation

Forms preserve safe selections, parameters, sample counts, filters and typed names
after failures.

### Retry and recovery

Retry is action-specific: provider/model changes, reload, retry job, adjust filters,
or confirm/cancel destructive action.

### Logging and correlation

Persist redacted job/action diagnostics with safe job/request identifiers; never log
secrets, raw support text or raw provider bodies.

### Negative-test strategy

Each work item covers validation, auth, project scope, not-found/conflict,
dependency failure, timeout/cancel, unknown code and no false success where relevant.

### Visual error-state verification

UI tasks collect browser evidence for changed error/empty/loading states.

### Removed or superseded error behavior

Profile- and candidate-specific errors are removed with their active workflows unless
a later task records a temporary compatibility bridge.

## Blockers

- None for T2. Later tasks still need their own work-item files before
  implementation.
