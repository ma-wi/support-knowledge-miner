# Review report: CHG-005-PROVIDER-SETTINGS-CENTRALIZATION / T008

- Reviewer: Codex
- Review scope: RB008 / T008 Explorer-Kontrollleiste, globaler Menübutton und Summary-Dialog
- Requirement and plan: `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/CHANGE.md`, `PLAN.md`, `DESIGN_DELTA.md`, `tasks/T008-explorer-control-rail-global-menu-summary-dialog.md`
- Commit or diff: local dirty worktree against `main`
- Revision: `26e98375f6330bfee7b47f3b60663549b6fe6685`
- Source digest: not-orchestrated local review; focused T008 patch-id `2ac1744b61e45f58e51ddc48c75b69cdaf4b233b`
- Date: 2026-08-06
- Verdict: changes-required
- Open P0/P1 findings: present

## Verdict

`REQUEST_CHANGES`

## Acceptance-criteria assessment

| Criterion | Status | Evidence |
|---|---|---|
| AC-1 | pass | Explorer loaded state renders left control rail with Cluster-Set, filter, outlier, Summary and export groups in `frontend/src/App.tsx`. |
| AC-2 | pass | Loaded Explorer composition has the export controls in the rail and no separate right export column. |
| AC-3 | pass | Topbar renders a `Hauptmenü öffnen` button in `frontend/src/App.tsx`. |
| AC-4 | pass | Overlay menu entries are Projekte, Einstellungen and Abmelden. |
| AC-5 | pass | Menu has accessible name, `aria-haspopup`, expanded state, Escape close and focus return. |
| AC-6 | pass | Menu Abmelden calls existing `signOut()` path. |
| AC-7 | partial | Cluster-Set Summary action opens an Option-A dialog, but that dialog has incomplete modal behavior. See P1-1. |
| AC-8 | pass | Explorer rail exposes Summary regeneration through the Summary-only endpoint. |
| AC-9 | pass | Frontend tests assert Summary endpoint use and no full Cluster-Set creation. |
| AC-10 | pass | UI copy explicitly says current Summary fields are replaced and version/copy modes are inactive. |
| AC-11 | pass | Export and Summary error state is rendered at rail/dialog surfaces and state is preserved. |
| AC-12 | fail | No desktop/mobile browser evidence, accessibility evidence, visual regression evidence, or independent visual-review report exists under `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/evidence/ui/`. See P1-2. |

## Work-item assessment

| Work item | Status before review | Review result | Evidence or finding |
|---|---|---|---|
| T008 | implemented | changes-required | P1-1 and P1-2 block advancing to reviewed. |

## Findings

### [P1-1] Summary dialog declares a modal dialog but does not implement required keyboard/focus behavior

- Location: `frontend/src/App.tsx` lines 3736-3819
- Problem: The new Summary regeneration dialog renders `role="dialog"` with `aria-modal="true"`, but it has no initial focus placement, no Escape close handling, no focus trap and no focus return to the opener. The existing source dialog implements these behaviors separately around lines 3400-3452, but the Summary dialog does not reuse or duplicate that modal behavior.
- Impact: Keyboard users can remain focused behind the modal or tab out of it while assistive technology is told the dialog is modal. This violates the accepted T008 accessibility direction for the Summary dialog and can make the Summary replacement action hard to operate or exit safely.
- Evidence: Code inspection of `frontend/src/App.tsx` shows refs/effects only for `sourceDialogCluster`; searches for `summaryDialog` show state and rendering but no equivalent focus/Escape effect. `frontend/src/App.test.tsx` covers opening and submitting the Summary dialog, but has no Escape, initial-focus, focus-trap or focus-return assertions for it.
- Required change: Add Summary dialog focus management equivalent to the source dialog or extract a shared modal helper. Cover at least initial focus, Escape close, Tab containment and focus return to the triggering Cluster-Set or Explorer Summary button.

### [P1-2] Required UI evidence and independent visual review are missing for design-class-3 production UI

- Location: `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/tasks/T008-explorer-control-rail-global-menu-summary-dialog.md` lines 228 and 306-311
- Problem: T008 is a design-class-3 UI production implementation, but AC-12 remains unchecked and no evidence files exist under `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/evidence/ui/`.
- Impact: Repo policy does not allow T008 to advance beyond code review without revision-bound desktop/mobile browser evidence, accessibility review, visual regression evidence and independent visual review. Code inspection and unit tests cannot substitute for that gate.
- Evidence: `find .ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/evidence -maxdepth 4 -type f` returned no files. The task itself lists browser, accessibility and visual-regression evidence as pending before review.
- Required change: Generate the required browser/accessibility/visual evidence for the exact revised worktree after P1-1 is fixed, then run the independent visual review and record the report.

## Incremental-change assessment

- Desired end state is coherent across all applicable layers: no, blocked by incomplete Summary dialog accessibility and missing required visual evidence.
- Every relevant impact row is classified and evidenced: no, UI evidence remains absent for T008.
- Existing responsibility was adapted rather than unnecessarily duplicated: yes.
- Retained legacy behavior has an accepted removal plan: yes for this T008 scope.
- Superseded artifacts were removed or explicitly tracked: yes for this T008 scope.
- Capability specifications describe current truth: yes for inspected T008 docs.
- Design classification and required evidence are valid: no, classification is valid but required evidence is absent.
- Review batch was coherent and within policy: yes.
- Notes: The review scope was T008 only. Earlier CHG-005 backend/migration/provider changes were not re-reviewed except where T008 depends on them.

## UI architecture

- [x] Existing components were reused where appropriate.
- [x] New shared components are justified, tested, demonstrated, and catalogued.
- [x] Production code does not depend on a temporary prototype.
- [x] Prototype-only dependencies were not promoted.
- [x] Replaced components were removed or deprecated for T008 scope.
- [x] Selected UI tooling is installed, locked, and owned by the correct package.

## Visual review

- Required: yes
- Status: pending
- Evidence manifest: missing
- Visual-review report: missing
- Reviewed revision/fingerprint: not available
- Open findings: P1-2

Code review must not mark required visual review as approved unless the independent
visual-review report exists for the same revision and fingerprint.

## Error contract

- [x] Applicable frontend mappings and unknown fallback remain centralized for inspected T008 paths.

## User-facing error behavior

- [x] Changed T008 actions have concrete failure states for export and Summary regeneration.
- [x] Input preservation, placement, retry, and no-false-success behavior are covered by frontend tests for export/Summary paths.

## Error security

- [x] No raw technical or sensitive details were observed in inspected T008 UI error copy.
- [x] OpenAI Summary confirmation remains tied to the Summary data-transfer action.

## Error tests

- [x] Frontend negative tests cover export error preservation and Summary-only endpoint behavior.
- [ ] Browser/visual error-state evidence is missing; see P1-2.

## Specification and test-seam assessment

- Specification status and readiness were valid: yes.
- Established domain terminology was followed: yes.
- Tests exercise the agreed observable seams: partial; dialog accessibility seams are missing.
- Unnecessary implementation-detail seams introduced: no.
- Notes: Unit tests are useful and focused, but do not cover the Summary modal accessibility contract.

## Verification performed

| Command or inspection | Result | Notes |
|---|---|---|
| `cd frontend && npm test -- --run src/App.test.tsx` | pass | 46 tests passed. npm emitted `Unknown env config "min-release-age"` warning. |
| `./.ai/tools/check-ui-quality.py` | pass | Static UI-quality artifact structure valid. |
| `./.ai/tools/check-work-state.py` | pass | Active work state structurally valid after this review status update. |
| `./.ai/tools/check-user-facing-errors.py` | pass | 36 catalog entries checked. |
| `git diff --check` | pass | No whitespace errors. |
| `find .ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/evidence -maxdepth 4 -type f` | fail | No UI evidence files found. |
| `./.ai/tools/verify.sh` | not run | Existing task evidence says it passed, but this reviewer did not rerun the full suite. |

## Security and compatibility assessment

### Security Assurance

- Security routing matches the actual diff: yes for T008.
- Security triggers: provider data transfer through Summary regeneration, global sign-out/session action, user-observable navigation and job actions.
- Assets, data classes, boundaries, and untrusted inputs: Cluster-Set IDs, provider/model IDs, session state, browser control state and LLM responses.
- Authorization model: unchanged authenticated, project-scoped API routes.
- Threats and abuse cases: accidental OpenAI text transfer, misleading Summary write semantics, inaccessible logout/menu or inaccessible modal flow.
- Mitigations at the protected boundary: OpenAI confirmation remains present; Summary endpoint is distinct from full Cluster-Set creation; sign-out reuses existing path; menu Escape/focus return exists.
- Negative verification and other evidence: frontend tests cover menu entries/Escape return, sign-out placement, Summary-only endpoint and export error preservation.
- Residual security risk: Summary modal accessibility is incomplete until P1-1 is fixed.
- Specialist security review: not separately required for T008 unless Summary version/copy persistence is added.
- Implementer adversarial pre-review complete: not observed for T008.

## Documentation assessment

T008 documentation updates are present in `docs/specifications/support-knowledge-miner-mvp1.md`, `docs/design/DESIGN_SYSTEM.md` and `docs/design/COMPONENT_CATALOG.md`. The design docs correctly keep visual evidence as pending rather than claiming completion.

## Residual risks and non-blocking notes

- The full repository diff is much larger than T008. This review intentionally did not re-review earlier CHG-005 tasks.
- The npm `min-release-age` warning did not fail the focused frontend test but should be cleaned up separately if it becomes a configured warning-as-error gate.
