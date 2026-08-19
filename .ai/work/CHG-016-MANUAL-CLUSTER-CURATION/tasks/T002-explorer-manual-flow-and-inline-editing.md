# Task T002: Explorer-Flow und Inline-Autosave

- Status: draft
- Parent requirement or change: `docs/requirements/chg-016-manual-cluster-curation.md`
- Plan: `.ai/work/CHG-016-MANUAL-CLUSTER-CURATION/PLAN.md`
- Work type: incremental-change
- Review batch: RB002
- Depends on: T001, approved `DESIGN_DELTA.md`
- Owner/agent: planner pending
- Last updated: 2026-08-19

## Objective

Den neuen manuellen Cluster-Erstellungs-/Vorschaufluss, die gezielte Einzel-Cluster-
LLM-Aktualisierung, die referenzbasierte Suche und die direkte Bearbeitung aller fünf
Clusterfelder im Explorer sicher, zugänglich und responsiv integrieren.

## Scope

### In scope

- Manual/LLM mode form, example/basis/scope/provider controls and preview selection.
- Create success refresh/switch to manual child.
- Per-cluster “Mit LLM aktualisieren” action with pending/success/error state.
- Source-dialog reference selection, basis/scope controls and result preview without
  implicit membership mutation.
- Inline title/category/FAQ question/answer editing with save on blur/commit.
- Immediate status save; remove row Save button.
- Pending/success/error/rollback states and central error mapping.
- Desktop/mobile browser, accessibility and visual evidence.

### Out of scope

- Backend domain or migration changes beyond consuming T001 contracts.
- Source removal mutation implementation (T003).

## Preconditions

T001 API contracts, error codes and approved class-2 design direction are available.

## Impact and responsibility

- `IMPACT.md` rows closed: UI, frontend model/validation, API client, errors,
  component impact and browser/visual evidence.
- Existing responsibility: extend `App.tsx` Explorer state and existing table/dialog/
  feedback patterns.
- New artifact: feature-local manual create/preview composition only if justified.
- Superseded artifact: row-level Save form removed after parity evidence.

## Affected files or components

`frontend/src/App.tsx`, `frontend/src/App.css`, `frontend/src/App.test.tsx`,
design/component documentation when required, and `.ai/work/.../evidence/ui/`.

## Acceptance criteria

- [ ] Empty mode requires and submits all four manual fields.
- [ ] Example mode handles loading, LLM-generated fields, preview, selection and
  creation without losing form/filter state on recoverable failure.
- [ ] A single cluster can be refreshed through the LLM; only its four displayed
  summary fields change and the UI refreshes no neighboring memberships.
- [ ] One or more source references can be selected; basis and all four scopes are
  accessible, results show scores/current clusters, and search alone does not mutate.
- [ ] All inline fields save without a separate Save button; failed optimistic writes
  restore the previous value and show actionable feedback.
- [ ] Status select saves immediately and disables duplicate requests.
- [ ] Focus, keyboard, labels, live regions, long text and mobile layout are covered.
- [ ] No raw API/exception/provider details are rendered.

## Security Assurance

- Security assurance: required
- Security triggers: confidential text in browser/API payloads, user-controlled IDs/
  fields, provider confirmation and mutation UI.
- Assets/data: examples, FAQ text, source snippets confidential; auth/session internal.
- Trust boundaries: browser state/API; API response/React rendering.
- Authorization model: rely on server T001; UI never infers permission from state.
- Threats/abuse cases: unsafe IDs, raw error disclosure, accidental duplicate saves,
  stale optimistic state, XSS through text rendering.
- Mitigations: typed/central API helper, escaped React text, bounded controls,
  explicit cloud checkbox, rollback and conflict handling.
- Security verification: frontend/API negative tests, no raw detail assertions,
  keyboard/accessible DOM checks and review.
- Residual risk: user may select a false-positive match; preview and explicit checkboxes
  keep assignment human-confirmed.
- Specialist security review: included with T001/T003 independent review.

## Error and recovery implementation

### User actions covered

- Load, create, preview/search, single-cluster refresh, reference selection, update
  inline, status update, retry/reload.

### Expected failures

Map all T001 codes through `normalizeApiError` and `ERROR_MESSAGES_BY_CODE`; field
errors attach to create inputs, preview/reference errors remain in their preview
region, single-summary errors remain on the affected cluster row and inline save
errors remain in the affected cell.

### Unknown failure behavior

Central safe fallback, correlation reference where available, no false success, draft
and filters retained, retry/reload offered.

### Required negative tests

- [ ] Validation/provider/no-result/conflict/network/timeout/unexpected/unknown code
- [ ] Failed optimistic update and no false success
- [ ] Input/selection/filter preservation, focus recovery and disabled-state recovery

### Error acceptance criteria

- [ ] Every changed action uses central normalization and safe actionable placement.
- [ ] Browser evidence covers relevant error, loading, empty, responsive and focus states.

## UI classification

- Design class: 2
- Prototype strategy: approved isolated prototype or React mock
- Visual review required: yes

## Component impact

### Existing components reused

Explorer rail/table, source/summary dialog patterns, semantic form controls, feedback
overlay, status chips, focus management, source selection and existing table scrolling.

### Existing components extended

Explorer row editor, single-summary action state, source-reference selection and
feature-local action/preview state.

### New shared components

none proposed; any new shared component needs catalog/API/test/accessibility evidence.

### New feature-local components

Manual-cluster creation/preview composition if `App.tsx` locality is insufficient.

### Components replaced or removed

Row-level Save form/button.

### Rejected reuse options

Separate page/editor or contenteditable-only controls without semantic keyboard/error
behavior.

### Rationale

Reuse maintains Explorer consistency while isolating the new class-2 flow.

## Prototype relationship

- Prototype artifact: pending design review
- Elements to promote: only approved flow/state decisions
- Prototype-only elements to discard: all mock API/data wiring
- Tool dependencies and owning package: existing frontend UI-quality package

## Visual evidence

- Required screens: manual form, preview, table inline edit, error and success states
- Required states: default/loading/empty/error/validation/submitting/success/long text/
  mobile/focus
- Required viewports: 1440x1000 and 390x844
- Manifest: `.ai/work/CHG-016-MANUAL-CLUSTER-CURATION/evidence/ui/manifest.json`

## Implementation constraints

Do not parse Problem Details locally in components or use raw HTML for support text.
Do not send a request per keystroke; commit on blur/Enter with a bounded pending
state and preserve safe local input.

## Applicable capability specification and test seam

- Specification criteria: Cluster Explorer table, summary fields, refinement/manual
  behavior and source dialogs.
- Primary observable boundary: rendered Explorer flow and API calls/state updates.
- Avoid direct tests of CSS internals; assert accessible roles, visible states and
  responsive/browser evidence.

## Verification

- [ ] `npm test`/configured frontend test wrapper and typecheck
- [ ] error-handling checker and UI browser/accessibility/visual commands
- [ ] full verify after all tasks

```bash
./.ai/tools/test.sh
./.ai/tools/ui-quality.sh browser
./.ai/tools/ui-quality.sh accessibility
./.ai/tools/ui-quality.sh visual-regression
```

## Risks or blockers

Design approval, final T001 field names and visual density of the preview on mobile.
