# Design Delta

## Metadata

- Change ID: CHG-005-PROVIDER-SETTINGS-CENTRALIZATION
- Design class: 3
- Highest design class assigned: 3
- Implementation-start design class: 3
- Status: approved
- Affected capability specifications: `docs/specifications/local-runtime-providers.md`, `docs/specifications/support-knowledge-miner-mvp1.md`
- Existing screens affected: Settings, Import, Indizieren, Cluster-Sets, Explorer,
  global feedback, app topbar/global navigation
- Prototype strategy: isolated-prototype
- Prototype artifact type: static-mockup
- Prototype artifact or revision: `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/prototype/settings-provider-centralization-mockup.html`
- Additional prototype artifacts: `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/prototype/project-workflow-adjustments-mockup.html`; `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/prototype/cluster-summary-explorer-optimization-mockup.html`
- Change base revision: 26e98375f6330bfee7b47f3b60663549b6fe6685
- Required visual gates: production implementation needs desktop/mobile browser
  evidence, accessibility, visual regression and independent visual review.
- Decision owner: anfordernder Product Owner
- Last updated: 2026-08-06

## Classification history

| Date | Previous class | New class | Reason | Approved by |
|---|---:|---:|---|---|
| 2026-08-05 | not-applicable | 3 | Settings information architecture changes and central provider-management flow | Product Owner |
| 2026-08-06 | 3 | 3 | Explorer workspace information architecture and global navigation placement change | Product Owner planning direction |

## Problem and user outcome

The user needs stable Settings layout without feedback-induced content jumps and a
clearer provider configuration model: connection settings are managed once, while
Embedding/LLM availability is controlled consistently with model allow-list
checkboxes.

## Current experience

- Feedback occupies content space and shifts the page.
- Provider connection settings and model-purpose settings are mixed.
- vLLM is shown although it should be removed from active UI/backend support.
- OpenAI, Ollama and vLLM cards use inconsistent model-entry patterns.
- Multiple provider instances cannot be represented in the current UI.

## Desired experience

- Feedback appears as a fixed overlay/popup with the existing status style.
- A new „Provider“ tab owns connection settings, API keys, endpoints, provider
  names, add/remove and Ollama model downloads.
- Separate „Embedding-Provider“ and „LLM-Provider“ settings tabs are removed.
- OpenAI and Ollama cards use the same visual structure and checkbox model
  selection. Separate Zweck-Checkboxen entfallen; usage is derived from selected
  Embedding/LLM models.
- Provider cards offer an explicit connection test.
- Model discovery updates available models without changing allow-lists until
  the user saves; unavailable models disappear after successful discovery.
- vLLM is absent from the visible UI and future active backend/API provider support.
- A running Ollama download is clearly visible and prevents starting another model
  download.
- Feedback overlay has a manual close button and still auto-dismisses.
- Import, Explorer and running-job behavior are clarified in a separate mockup.
- Explorer uses a left control rail for Cluster-Set selection, search/filter,
  outlier controls, Summary regeneration and export.
- The global app navigation is not a persistent left sidebar in the Explorer
  workspace. A top-right menu button opens an overlay menu with Projekte,
  Einstellungen and Abmelden.
- Cluster-Sets retain Summary regeneration as a compact card action that opens a
  dialog. Explorer also exposes Summary regeneration in the left control rail.

## User flow

1. User opens Settings.
2. User selects „Provider“.
3. User adds OpenAI or Ollama, or edits an existing provider instance.
4. User names the provider, enters connection details and can test the connection.
5. User fetches/discovers models or starts an Ollama model download.
6. User selects allowed Embedding and LLM models via checkboxes and saves.
7. In project flows, user later selects the configured provider instance and model.
8. Import logs show dates and expose validation details only when available.
9. Explorer auto-loads the last updated completed Cluster-Set and hides export when
   no Cluster-Set exists.
10. Running indexing/cluster-set jobs remain cancellable while additional bounded
    jobs can be queued/started.
11. User opens the Explorer; the left control rail owns set switching, filters,
    outlier refinement, Summary regeneration and export.
12. User opens global navigation through the top-right menu button and can choose
    Projekte, Einstellungen or Abmelden.
13. User can start Summary regeneration either from a Cluster-Set card dialog or
    from the Explorer control rail without recalculating cluster assignments.

## Screen inventory

| Screen or state | Existing | Changed | New | Notes |
|---|---:|---:|---:|---|
| Settings tab navigation | yes | yes | no | Keep only „Provider“ and „Nutzer“ |
| Provider central connection tab | no | no | yes | New owner for connection/API key/endpoint/add/remove |
| Embedding-Provider tab | yes | yes | no | Removed from Settings |
| LLM-Provider tab | yes | yes | no | Removed from Settings |
| Global feedback overlay | yes | yes | no | Same visual style, fixed overlay placement |
| Ollama download in progress | yes | yes | no | Current behavior has status only; mockup shows progress-capable pattern |
| vLLM visible configuration | yes | yes | no | Removed from active UI target |
| Import protocols | yes | yes | no | Add date and clarify/remove details action |
| Explorer default/empty | yes | yes | no | Auto-load last updated completed set; no export panel when no cluster exists |
| Explorer left control rail | no | no | yes | Owns set switching, search/filter, outliers, Summary regeneration and export |
| Global top-right menu button | no | no | yes | Replaces persistent global sidebar in Explorer workspace and standalone Abmelden button |
| Summary regeneration dialog | yes | yes | no | Cluster-Set card opens dialog; Explorer can open same Summary action from rail |
| Bounded job start states | yes | yes | no | Do not disable indexing/cluster starts solely because another job is active; backend queue/resource limits remain the rejection seam; keep cancel |

## State inventory

- default: Provider cards show connection controls, model allow-lists and actions.
- loading: Overlay status and card-local progress indicate model download or model
  discovery.
- empty: Provider tab shows add-provider control; Explorer shows no export panel when
  no Cluster-Set exists.
- error: Provider-card form banner plus overlay error summary; messages are safe and
  actionable.
- validation: Required provider name, endpoint/API key where needed, and model name
  validation before save/download.
- disabled: Second Ollama download button disabled while another download is active.
  Indexing/cluster start buttons are not disabled solely because another job is
  active.
- submitting: Save/check actions should disable only the affected card actions.
- success: Overlay success plus updated card status/model list.
- long content: Provider list stacks cards and keeps model checkbox lists scrollable
  only if needed.
- small viewport: Sidebar stacks above content; provider cards become one column.
- Explorer small viewport: global navigation stays behind the top-right menu button;
  the Explorer control rail stacks above the table or collapses into sections before
  the wide table.
- permission restricted: Not designed yet; if settings become role-restricted, show
  page-level access state.
- partial data: Failed model discovery preserves existing allowed models and shows
  retry.

## Responsive behavior

The prototype follows the current `980px` breakpoint: sidebar and all provider grids
collapse to one column. The overlay uses a bounded width and in narrow viewports spans
the available width with left/right margins.

## Component impact

### Existing components reused

- App shell/topbar/sidebar/page tabs.
- Provider card/panel layout.
- Status/feedback visual variants.
- Existing inline checkbox styling.

### Existing components extended

- Provider forms become provider-instance cards that contain connection settings,
  connection test, model discovery and purpose-specific model checkboxes in one
  place.
- Feedback message gains fixed overlay placement.
- App shell/topbar replaces the visible Abmelden-only action with a top-right menu
  button for Projekte, Einstellungen and Abmelden.
- Explorer table composition gains a left control rail and removes the right-side
  export column from the active target layout.
- Cluster-Set cards keep Summary regeneration as a dialog action.

### New shared components

| Name/responsibility | Target path/layer | API/variants/states | Tests | Accessibility | Story/equivalent | Catalog entry |
|---|---|---|---|---|---|---|
| none | not-applicable | not-applicable | not-applicable | not-applicable | not-applicable | not-applicable |

### New feature-local components

- Provider instance card for Settings.
- Ollama download progress block.
- Add-provider toolbar.
- Import protocol row with conditional validation-details action.
- Explorer empty/default Cluster-Set state.
- Explorer control rail.
- Global top-right menu overlay.
- Summary regeneration dialog content shared conceptually between Cluster-Sets and
  Explorer.
- Parallel queued/running job state.

### Components replaced or removed

- Free-text OpenAI LLM model field.
- Free-text Ollama LLM model field, if model discovery/pull provides selectable
  model candidates.
- Separate Settings tabs „Embedding-Provider“ and „LLM-Provider“.
- Visible/active vLLM UI and future backend provider support.
- Export panel when no Cluster-Set exists.
- Right-side Explorer export column in loaded Explorer state.
- Persistent global sidebar in the Explorer workspace.
- Standalone topbar `Abmelden` button in the Explorer workspace.

### Rejected reuse options

- Reusing current separate provider settings tabs unchanged: fails centralization
  requirement and user feedback.
- Reusing free-text model fields: fails consistency requirement.
- Treating multiple Ollama endpoints as only display-name aliases: fails identity and
  provenance requirements.

### Rationale

The design keeps current density and visual language while simplifying ownership:
provider connection, purpose availability and model allow-lists are handled in the
single Provider tab.

## Design-system impact

- docs/design/DESIGN_SYSTEM.md impact: Update Settings/provider section after
  approval to describe the single Provider tab, overlay feedback and project workflow
  adjustments.
- docs/design/COMPONENT_CATALOG.md impact: Update Provider forms responsibility and
  Feedback message placement after implementation.
- Tokens: No new color/radius/shadow tokens expected.
- Accessibility: Overlay uses `role=status` or `role=alert`, not toast-only for
  primary failures; card-local errors remain near affected controls.
- Responsive behavior: Existing one-column collapse is retained.
- Existing-screen/component migration: Settings tabs, project provider selects,
  Import protocols, Explorer default loading/export visibility and bounded
  queued/running job states need migration.
- Project-wide visual-regression impact: Settings, Indizieren and Cluster-Set form
  screenshots likely change. Explorer loaded/table/export screenshots and app
  topbar/navigation screenshots change.

## Accessibility requirements

- Settings tabs retain `role=tablist` / `role=tab`.
- Every input, checkbox and button has visible text.
- Overlay status uses live-region semantics, has a labelled close button and does
  not steal focus.
- The global menu button has an explicit accessible name, `aria-haspopup`, accurate
  expanded state, keyboard activation, Escape close, outside-click close, focus
  return to the opener and safe logout semantics.
- Explorer control rail sections have headings and remain keyboard reachable before
  the table.
- Form errors remain close to provider card controls.
- Long-running download state is announced and visually represented.
- Disabled download action includes explanatory text.

## Error experience

### Action and failure inventory

| Action | Failure | Error code | User message | Placement | Recovery action |
|---|---|---|---|---|---|
| Save provider | Invalid endpoint/API failure | `VALIDATION_FAILED` | Provider-Konfiguration konnte nicht gespeichert werden. Eingaben prüfen und erneut versuchen. | Provider card banner + overlay summary | Correct input/retry |
| Check provider | Endpoint unavailable/auth rejected | `VALIDATION_FAILED` | Verbindung konnte nicht geprüft werden. Endpoint/API-Key prüfen und erneut versuchen. | Provider card status + overlay summary | Correct/retry |
| Remove provider | Hard delete fails | `PROVIDER_DELETE_FAILED` | Provider konnte nicht entfernt werden. Historie bleibt erhalten; bitte erneut versuchen. | Provider card | Retry/reload |
| Remove provider | Active job still references provider | `PROVIDER_DELETE_BLOCKED` | Provider wird noch von einer aktiven Berechnung verwendet. Bitte Abschluss abwarten oder den Job abbrechen. | Provider card | Wait/cancel |
| Pull Ollama model | Another pull running | `PROVIDER_MODEL_PULL_IN_PROGRESS` | Ein Modell-Download läuft bereits. Bitte Abschluss abwarten. | Download row + overlay info | Wait |
| Pull Ollama model | Pull timeout/failure | `VALIDATION_FAILED` | Ollama-Modell konnte nicht geladen werden. Modellname und Verbindung prüfen. | Download row + overlay error | Retry |
| Open Explorer | No completed Cluster-Set | not-applicable | Noch kein Cluster-Set vorhanden. Erstelle zuerst ein Cluster-Set. | Explorer panel | Go to Cluster-Sets |
| Open global menu | Menu cannot be rendered | not-applicable | not-applicable; static client-side menu must fail closed with no action | Topbar | Retry reload |
| Summary neu erstellen | LLM provider/model unavailable | `LLM_PROVIDER_UNAVAILABLE` | Provider/Modell ist nicht verfügbar. Einstellungen prüfen und erneut versuchen. | Cluster-Set dialog or Explorer control rail | Choose provider/model or retry |
| Summary neu erstellen | Summary generation fails | `CLUSTER_SUMMARY_FAILED` | Zusammenfassung konnte nicht erstellt werden. Cluster bleiben erhalten. | Cluster-Set dialog or Explorer control rail | Retry/change model |
| Start indexing | Local queue capacity exhausted | `UNEXPECTED_ERROR` | Die Indizierung konnte nicht gestartet werden. Bitte später erneut versuchen. | Indexing form | Retry later |
| Start Cluster-Set | Local queue capacity exhausted | `UNEXPECTED_ERROR` | Das Cluster-Set konnte nicht gestartet werden. Bitte später erneut versuchen. | Cluster-Set form | Retry later |

### Error presentation levels

- Inline field error: invalid provider name, URL, required API key/new model name,
  invalid job parameters.
- Form-level banner: save/check/delete/download failure.
- Component-level error: failed model discovery for one provider card.
- Page-level error: settings/provider list cannot load.
- Toast or transient notification: supplementary success/info overlay only.
- Fatal application fallback: unchanged existing app-level unexpected failure path.

### Input preservation

Provider name, endpoint, available-model list and selected model checkboxes remain
available after failed save/check. API key input should be cleared or preserved only
according to the accepted secret-input policy; saved key plaintext is never
displayed.

### Focus behavior

- Field validation failure: focus invalid field.
- Form submission failure: keep focus in affected card and expose banner as alert.
- Page-level load failure: focus retry action.
- Dialog action failure: not applicable in current mockup.

### Recovery behavior

- Retry: save, check, discover, pull.
- Reload: provider list load failure.
- Reauthenticate: existing auth flow if API returns unauthorized.
- Return to previous page: not primary recovery.
- Contact support: not applicable for local MVP unless unexpected failure persists.
- Resolve conflict: provider deletion/history conflicts need accepted behavior.
- Correct input: endpoint, name, API key, model name.

### Unknown error fallback

- User-facing title: Aktion konnte nicht abgeschlossen werden.
- User-facing explanation: Die Provider-Aktion ist unerwartet fehlgeschlagen. Bitte
  erneut versuchen oder den aktuellen Stand neu laden.
- Correlation ID placement: only if backend supplies a safe reference.
- Support instruction: not applicable for MVP unless a safe reference exists.
- Input preservation: preserve non-secret fields and selections.
- Retry behavior: re-enable actions after loading state ends.

### Error-state evidence

- Mockup:
  `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/prototype/settings-provider-centralization-mockup.html`
- Mockup:
  `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/prototype/cluster-summary-explorer-optimization-mockup.html`
- Prototype: not-applicable
- Storybook: not-applicable
- Browser screenshots: not captured in this draft

For design class 2 or 3, every relevant central action must show its error states in
the approved artifact before `Status: approved`.

## Prototype or mockup plan

Create static HTML mockups with no production imports. Include:

- Provider centralization screen.
- Feedback overlay.
- Ollama download progress and disabled second-download state.
- Desktop and responsive CSS matching existing visual language.
- Import protocol date/logdetails state.
- Explorer default/empty/export-hidden state.
- Bounded indexing/cluster-set queued/running state without global start blocking.
- Explorer control rail with search/filter, outlier controls, Summary regeneration
  and export.
- Top-right global menu button and overlay menu containing Projekte, Einstellungen
  and Abmelden.
- Cluster-Set Summary regeneration dialog.

## Prototype isolation

- Production imports allowed: no
- Production build inclusion allowed: no
- Production backend connection allowed: no
- Production runtime dependency allowed: no
- Mock data or local fixtures: inline static sample providers/models only
- Private and non-deployable: yes
- Required tool dependencies and owning package: none

## Mockup or prototype evidence

- Static artifact:
  `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/prototype/settings-provider-centralization-mockup.html`
- Static artifact:
  `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/prototype/project-workflow-adjustments-mockup.html`
- Static artifact:
  `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/prototype/cluster-summary-explorer-optimization-mockup.html`
- README:
  `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/prototype/README.md`

## Prototype promotion decisions

| Prototype element | Decision | Target path | Target layer/responsibility | Tests | Story | Accessibility | Catalog update |
|---|---|---|---|---|---|---|---|
| Feedback overlay | extend-existing-production-component | `frontend/src/App.tsx`, `frontend/src/App.css` | App-wide feedback | Frontend tests for no content reflow/live role | Browser evidence | role status/alert, no focus steal | update Feedback message |
| Provider instance card | create-feature-local-component | `frontend/src/App.tsx` or extracted settings component | Settings provider connection owner | Provider settings tests | Browser evidence | labels, alerts, keyboard | update Provider forms |
| Add-provider toolbar | create-feature-local-component | Settings UI | Add OpenAI/Ollama instances | Form/action tests | Browser evidence | labelled select/button | update Provider forms |
| Ollama download progress | create-feature-local-component | Settings provider card | Pull status and one-download guard | Pull progress/disabled tests | Browser evidence | progress semantics | update Provider forms |
| Import protocol details/date | extend-existing-production-component | `frontend/src/App.tsx` | Import protocol row | Frontend import tests | Browser evidence | conditional action text | update Import panels if needed |
| Explorer auto-load/export-hidden | extend-existing-production-component | `frontend/src/App.tsx` | Explorer default/empty state | Explorer tests | Browser evidence | status text and no hidden export controls | update Explorer export panel if needed |
| Explorer left control rail | implement-page-composition | `frontend/src/App.tsx`, `frontend/src/App.css` | Cluster-Set switching, filters, outlier controls, Summary regeneration and export | Explorer layout/action tests | Browser evidence | labelled sections and controls before table | update Explorer table/export panel |
| Global top-right menu overlay | extend-existing-production-component | `frontend/src/App.tsx`, `frontend/src/App.css` | Projekte/Einstellungen/Abmelden global navigation without persistent Explorer sidebar | navigation/menu/focus tests | Browser evidence | menu button name, expanded state, Escape/focus return | update App shell |
| Cluster-Set Summary dialog | extend-existing-production-component | `frontend/src/App.tsx`, `frontend/src/App.css` | Summary-only regeneration from Cluster-Sets and Explorer | frontend/API compatibility tests | Browser evidence | modal semantics or equivalent dialog controls | update Cluster-Set tree cards |
| Bounded job start states | extend-existing-production-component | `frontend/src/App.tsx` + backend services | Allow indexing/cluster starts unless backend queue/resource preflight rejects; keep queued/running/cancel states visible | API/frontend concurrency tests | Browser evidence | enabled controls, safe backend rejection feedback and cancel controls | update Indexing/Cluster cards if needed |
| Static mock data/styles | discard-prototype-only-code | not-applicable | not-applicable | not-applicable | not-applicable | not-applicable | not-applicable |

## Open design decisions

No unresolved design decision blocks CHG-005 or T008 readiness. The items below are
either resolved for the current scope or explicitly deferred outside the current
implementation scope.

### Resolved for current scope

1. Provider usage is derived from the Embedding and LLM model allow-lists. Separate
   Provider-purpose checkboxes are removed. A model can be allowed independently for
   Embedding and LLM when the provider/model capability supports that purpose.
2. Historical `provider`+`model` provenance is displayed as a read-only snapshot:
   persisted provider display name, provider base type and model remain visible on
   existing import/indexing/Cluster-Set records after provider migration, rename or
   hard deletion. Active provider renames/deletions do not rewrite historical
   provenance snapshots.
3. OpenAI API-key display uses only a fully masked placeholder such as
   „•••••••• gespeichert“; no real key prefix is shown.
4. Summary regeneration in Explorer initially replaces the existing Summary fields
   through the Summary-only path. „Als Summary-Version speichern“ and
   „Cluster-Set-Kopie mit neuer Summary“ stay disabled or absent until backend
   persistence, provenance and rollback semantics are accepted.
5. The global menu uses a three-bar icon in the target mockup. The profile icon was
   rejected because the menu is not limited to account actions.

### Deferred outside current implementation scope

1. Ollama download progress can initially show running/final-success/final-failure.
   Percentage or streaming progress remains deferred until a reliable streaming seam
   is accepted.

## Approval

- Decision: approved
- Approved direction: Approved by Product Owner in the 2026-08-05 implementation go-ahead for the mockup.
- Approved artifact or revision: `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/prototype/settings-provider-centralization-mockup.html`
- Approval type: human
- Approved by: anfordernder Product Owner
- Date: 2026-08-05
