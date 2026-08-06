# Task T008: Explorer-Kontrollleiste, globaler Menübutton und Summary-Dialog

- Status: verified
- Parent requirement or change: CHG-005-PROVIDER-SETTINGS-CENTRALIZATION
- Plan: `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/PLAN.md`
- Work type: incremental-change
- Review batch: RB008
- Depends on: T004,T006
- Owner/agent: Codex
- Last updated: 2026-08-06

## Objective

Implement the Explorer workspace redesign when an implementation context starts:
the Explorer uses a left control rail, the global app menu moves to a top-right
menu button, Summary regeneration is available in the Explorer, and Cluster-Sets
keep Summary regeneration as an Option-A dialog.

## Accepted UI direction

- Explorer loaded state:
  - left control rail contains Cluster-Set switching, search/filter controls,
    outlier controls, Summary regeneration and export;
  - table remains the main right-side workspace;
  - table actions remain visible, with sticky action column as the preferred
    supporting table pattern if horizontal scroll remains necessary.
- Global navigation:
  - no persistent global sidebar in any signed-in view;
  - top-right menu button occupies the current visible `Abmelden` location;
  - menu icon is the three-bar icon;
  - overlay menu entries are exactly: Projekte, Einstellungen, Abmelden.
- Summary regeneration:
  - Cluster-Sets expose `Summaries neu erstellen` as a compact card action opening
    the dialog pattern from the mockup;
  - Explorer exposes Summary regeneration in the left control rail;
  - Summary regeneration must not recalculate cluster assignments.

## Mockup and design artifact

- Isolated prototype:
  `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/prototype/cluster-summary-explorer-optimization-mockup.html`
- This artifact is temporary, private and not production code.
- Production implementation must reimplement the target behavior through
  `frontend/src/App.tsx` and `frontend/src/App.css`; it must not import prototype
  code or mock data.

## Scope for future implementation

### In scope

- Replace the loaded Explorer right-side export panel with a left Explorer control
  rail.
- Move Explorer search, category/status/excluded controls, outlier refinement,
  Summary regeneration and export controls into the rail.
- Replace the visible topbar `Abmelden` action with a top-right menu button.
- Add a global overlay menu with Projekte, Einstellungen and Abmelden.
- Remove the persistent left global sidebar from all signed-in layouts; project
  switching remains available through the project overview opened from the menu.
- Keep Cluster-Set Summary regeneration as a dialog.
- Wire Explorer Summary regeneration to the existing Summary-only API path.
- Preserve current Explorer filters and export format state across failed export or
  Summary regeneration attempts where safe.
- Preserve existing project-tab workflow labels unless a separate accepted change
  changes navigation labels.

### Out of scope unless separately accepted

- Implementing a durable Summary-version history.
- Implementing Cluster-Set copies solely for alternate Summary outputs.
- Changing clustering, embeddings, source dialogs or export file content.
- Introducing a routing library or external UI component dependency.
- Reintroducing a persistent global sidebar in any signed-in layout.

## Summary write-mode decision

- Initial implementable mode: replace current Summary fields for the loaded
  Cluster-Set via the existing Summary-only regeneration flow.
- Planned but not ready without backend acceptance:
  - save as separate Summary version;
  - create a Cluster-Set copy with new Summary output.
- If the UI shows planned modes before backend support exists, they must be disabled
  with explanatory text, not silently mapped to replace.

## Security Assurance

- Security assurance: required
- Security triggers: provider data transfer, global sign-out/session action,
  user-observable navigation and job actions.
- Assets and data classes: imported support texts used as Summary examples,
  provider/model IDs, Cluster-Set IDs, session state.
- Trust boundaries and untrusted inputs: browser form/control state, provider/LLM
  responses, Summary regeneration payloads.
- Authorization model: unchanged authenticated, project-scoped API routes.
- Threats and abuse cases: accidental OpenAI text transfer from Explorer Summary
  action, misleading Summary write-mode creating untracked data semantics, logout
  hidden in inaccessible menu, menu focus/keyboard traps or actions firing
  accidentally.
- Mitigations: OpenAI confirmation remains tied to concrete Summary data-transfer
  action; replace/version/copy semantics must be explicit and tested; menu button
  has accessible name, expanded state, Escape close and focus return; Abmelden
  remains visible inside the menu and uses existing sign-out behavior.
- Security verification: frontend tests for menu entries and sign-out action
  placement, API/frontend tests for Summary-only regeneration path, negative tests
  for failed Summary regeneration preserving clusters.
- Residual security risk: Summary-version and Cluster-Set-copy write modes remain
  disabled or absent until backend persistence, provenance and rollback semantics
  are accepted and reviewed.
- Specialist security review: not separately required beyond normal CHG-005 review
  unless Summary-version/copy persistence is added.

## Error and recovery implementation

### User actions covered

Open global menu, Abmelden from menu, Explorer export, Summary regeneration from
Cluster-Sets dialog and Summary regeneration from Explorer control rail.

### Expected failures

| Action | Failure | Error code | Safe user message | Placement | Recovery | Retry | Input preservation | Tests | Logging/correlation |
|---|---|---|---|---|---|---|---|---|---|
| Open global menu | Client menu cannot render | not-applicable | not-applicable; fail closed with no action | Topbar | Reload page | yes, reload | not-applicable | frontend menu render test | not-applicable: client-only fail-closed state; no diagnostic payload required |
| Abmelden from menu | Session revoke fails | existing auth fallback | Abmeldung konnte nicht abgeschlossen werden. Bitte erneut versuchen. | Menu/global feedback | Retry | yes | not-applicable | existing auth tests plus menu action test | Existing auth/session revocation logging only; no session secret or user text in client logs |
| Explorer export | No visible rows or too large | existing export codes | Existing safe export messages | Explorer control rail | Adjust filters/retry | yes after filter/export correction | Search/filter/export format preserved | frontend/API export tests | Existing export request/error logging with safe project/export references only |
| Summary neu erstellen | Provider/model unavailable | `LLM_PROVIDER_UNAVAILABLE` | Provider/Modell ist nicht verfügbar. Einstellungen prüfen und erneut versuchen. | Summary dialog or Explorer rail | Choose another provider/model or retry | yes after provider/model correction | Selected safe controls preserved | service/API/frontend tests | Safe provider/model/Cluster-Set/job references only; no raw support text, prompt, provider response or secret |
| Summary neu erstellen | Summary generation fails | `CLUSTER_SUMMARY_FAILED` | Zusammenfassung konnte nicht erstellt werden. Cluster bleiben erhalten. | Summary dialog or Explorer rail | Retry/change model | yes | Existing clusters remain loadable | service/API/frontend tests | Safe Cluster-Set/job/correlation reference only; diagnostics redacted and bounded |
| Summary neu erstellen | OpenAI confirmation missing | existing cloud-confirmation code | OpenAI-Übertragung für diese Aktion bestätigen. | Summary dialog or Explorer rail | Confirm or choose local model | yes after confirmation or local-provider selection | Provider/model/sample controls preserved | API/frontend tests | Safe validation/correlation reference only; no example text, prompt, provider response or API key |

### Unknown failure behavior

- User-facing fallback: existing safe `UNEXPECTED_ERROR` or action-specific fallback.
- Correlation ID: only safe backend request/job identifiers if already supplied.
- Retry behavior: retry menu action, export or Summary action after correction.
- Input preservation: preserve search/filter/export format and safe Summary controls.
- Support behavior: reload project state; inspect sanitized Cluster-Set diagnostics.

### Required negative tests

- [x] Menu Escape close and focus return.
- [x] Abmelden is reachable only through the menu and still uses existing sign-out.
- [x] Export errors preserve rail filters and format.
- [x] Explorer Summary regeneration calls only the Summary endpoint.
- [x] Cluster-Set Summary dialog does not call full Cluster-Set creation.
- [x] Failed Summary regeneration preserves existing clusters.

## Component impact

### Existing components reused

- App shell/topbar, panel/card styling, buttons, form controls, feedback overlay,
  Explorer table, Cluster-Set cards and Source dialog.

### Existing components extended

- App shell/topbar: replace standalone `Abmelden` with menu button and overlay.
- Explorer table page composition: add left control rail and remove right export
  column.
- Explorer export panel: move controls into the rail.
- Outlier box: move into the rail while preserving child Cluster-Set semantics.
- Cluster-Set cards: Summary regeneration opens the dialog pattern.

### New shared components

- none planned.

### New feature-local components

- Explorer control rail.
- Global menu overlay.
- Summary regeneration dialog, feature-local unless a later shared dialog standard
  is accepted.

### Components replaced or removed

- Persistent global sidebar in all signed-in layouts.
- Standalone topbar `Abmelden` button.
- Loaded Explorer right-side export column.

### Rejected reuse options

- Keeping export on the right is rejected because it competes with table width.
- Keeping Summary regeneration only on Cluster-Sets is rejected because Summary
  quality is judged in the Explorer.
- Adding Cluster-Set copies by default for new summaries is rejected until copy
  provenance and rollback semantics are accepted.

### Rationale

The Explorer is the main curation workspace. A left rail groups controls by action
type, while the table keeps the largest available width. The global menu button
removes secondary navigation from signed-in workspaces without removing access.

## UI classification

- Design class: 3
- Prototype strategy: isolated-prototype
- Visual review required: yes after production implementation

## Visual evidence

- Required screens: topbar menu closed/open, Explorer loaded state with left
  control rail, Explorer table with visible actions, Cluster-Set Summary dialog,
  Explorer Summary controls and export controls.
- Required states: default, menu open, Summary provider/model unavailable,
  Summary generation failed, export failure/no visible rows and mobile stacked rail.
- Required viewports: desktop and mobile through CHG-005 visual review.
- Manifest: deferred until production implementation and browser evidence.

## Acceptance criteria

- [x] AC-1: Loaded Explorer shows a left control rail with Cluster-Set, search/filter,
  outlier, Summary and export groups.
- [x] AC-2: Loaded Explorer has no separate right-side export panel.
- [x] AC-3: The global topbar shows a top-right menu button in the former visible
  `Abmelden` area.
- [x] AC-4: The global overlay menu contains exactly Projekte, Einstellungen and
  Abmelden.
- [x] AC-5: The menu button has an accessible name, `aria-haspopup`, accurate
  expanded state, Escape close and focus return.
- [x] AC-6: Abmelden from the overlay uses the existing sign-out/revocation behavior.
- [x] AC-7: Cluster-Sets expose Summary regeneration through an Option-A dialog.
- [x] AC-8: Explorer exposes Summary regeneration in the left control rail.
- [x] AC-9: Summary regeneration uses the Summary-only path and never recalculates
  cluster assignments.
- [x] AC-10: Initial Summary write behavior is explicit replacement of current
  Summary fields; version/copy options are disabled or absent until backend semantics
  are accepted.
- [x] AC-11: Export and Summary errors appear at the rail/dialog surface and preserve
  safe user input.
- [ ] AC-12: Desktop and mobile browser evidence covers menu closed/open, Explorer
  rail, loaded table, Summary dialog and export controls.

## Implementation sequence for future work

1. Update App shell/topbar state for top-right menu button and overlay.
2. Move Explorer controls into a feature-local rail while preserving existing state
   variables and handlers.
3. Move export controls into the rail and remove the loaded-state right export
   panel.
4. Add Summary regeneration entry in the rail using the existing Summary-only
   API flow.
5. Convert Cluster-Set Summary action to the dialog pattern.
6. Add/adjust frontend tests for menu, rail, export, Summary dialog and failure
   states.
7. Update current-state specs and design docs.
8. Run focused frontend tests, affected backend/API tests if Summary payloads change,
   accessibility/browser/visual evidence and then full verification.

## Verification plan

- Frontend tests:
  - menu opens/closes and contains Projekte, Einstellungen, Abmelden;
  - Abmelden action is reachable through the menu;
  - Explorer control rail renders loaded set controls;
  - export uses current filtered state from the rail;
  - Summary regeneration from Explorer calls Summary-only endpoint;
  - Cluster-Set Summary button opens dialog and does not call full clustering.
- Backend/API tests:
  - only needed if Summary payloads or write-mode semantics change beyond existing
    T006 endpoint behavior.
- UI quality:
  - desktop and mobile browser evidence;
  - accessibility review for menu and Summary dialog;
  - visual regression update for Explorer loaded state and topbar.
- Full gate before review:
  - `./.ai/tools/verify.sh`.

## Readiness decision

- Ready for implementation: yes
- Released by: anfordernder Product Owner
- Release date: 2026-08-06
- Implementation started: yes
- Notes: Product Owner released T008 on 2026-08-06. Production UI implementation and
  remediation are complete for code/test/docs scope; browser/accessibility/visual
  evidence remains pending before UI-quality review.

## Implementation result

- App shell: standalone visible `Abmelden` topbar action replaced with a top-right
  three-bar menu. The menu exposes exactly Projekte, Einstellungen and Abmelden,
  has `aria-haspopup`/expanded state, closes on Escape/outside click and returns
  focus to the opener on Escape. The persistent left global sidebar was removed
  from all signed-in layouts.
- Explorer: loaded state now uses a left control rail for Cluster-Set switching,
  search/filter, outlier recalculation, Summary regeneration and export. The old
  right-side export panel was removed from the loaded Explorer composition. The
  table action column is more compact and keeps actions aligned in a single column.
- Summary: Cluster-Set cards and the Explorer rail now open an explicit Option-A
  replacement dialog with provider, model, sample and result controls. Explorer
  rail Summary regeneration uses the same Summary-only endpoint path and does not
  call full Cluster-Set creation.
- Backend robustness: Cluster Summary parsing still prefers schema JSON, but now
  accepts common LLM variants with German labeled fields or typographic quotation
  marks instead of failing with `Cluster summary response contains no parseable JSON
  object`.
- Error handling: export failures remain in the rail and preserve filter/format
  state; Summary failures render on the dialog or rail surface and also use global
  feedback.
- Documentation: updated `docs/specifications/support-knowledge-miner-mvp1.md`,
  `docs/design/DESIGN_SYSTEM.md` and `docs/design/COMPONENT_CATALOG.md`.

## Verification evidence

- `cd frontend && npm test -- --run src/App.test.tsx` — passed, 46 tests.
- `./.ai/tools/format.sh --check` — passed.
- `./.ai/tools/lint.sh` — passed.
- `cd frontend && npm run build` — passed.
- `PYTHONPATH=. uv run pytest tests/clusters/test_cluster_service.py -q` — passed,
  55 tests.
- `npm --prefix frontend test -- --run App.test.tsx` — passed, 46 tests.
- `./.ai/tools/check-docs.py` — passed with 5 budget warnings and no errors.
- `./.ai/tools/check-user-facing-errors.py` — passed.
- `./.ai/tools/verify.sh` — passed; 225 backend tests, 46 frontend tests and 5
  Bats tests included.

### Adversarial pre-review

- Adversarial pre-review: passed
- Pre-review lenses: UI quality, user-facing errors, provider-data security,
  Summary-only API compatibility, keyboard accessibility, responsive Explorer table
  layout, documentation consistency.
- Pre-review evidence: persistent left global sidebar removed from signed-in DOM and
  guarded by tests; Summary dialog has provider/model/sample/result controls,
  Escape/Tab/focus-return modal behavior and no browser `confirm()` fallback;
  Summary regeneration posts only to the Summary-only endpoint; parser regression
  tests cover labeled-text and typographic-quote LLM variants; `./.ai/tools/verify.sh`
  passed after code/test/docs changes.
- Open P0/P1 findings: none

## Review outcome

- 2026-08-06 code review verdict: `REQUEST_CHANGES`.
- Required remediation:
  - add Summary dialog keyboard/focus handling equivalent to the existing modal
    behavior and cover it with tests;
  - generate required desktop/mobile browser, accessibility, visual regression and
    independent visual-review evidence after code remediation.
- Review report: `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/REVIEW.md`

## Pending evidence before review

- Desktop/mobile browser evidence for menu closed/open, Explorer rail, loaded table,
  Summary dialog and export controls.
- Accessibility review for the menu and Summary dialog.
- Visual regression update/review for Explorer loaded state and topbar.
