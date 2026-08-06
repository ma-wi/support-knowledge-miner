# Task T001: Settings-Provider-Mockup erstellen

- Status: verified
- Parent requirement or change: CHG-005-PROVIDER-SETTINGS-CENTRALIZATION
- Plan: `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/PLAN.md`
- Work type: incremental-change
- Review batch: RB001
- Depends on: none
- Owner/agent: Codex
- Last updated: 2026-08-05

## Objective

Create an isolated static mockup for the requested Settings changes and record
questions/implementation notes without changing production code.

## Scope

### In scope

- New Provider tab mockup.
- Removed Embedding-Provider and LLM-Provider settings tabs in the mockup.
- Separate project workflow adjustment mockup.
- Feedback overlay mockup.
- Ollama download progress/disabled state mockup.
- Technical/fachliche assessment notes.

### Out of scope

- React/FastAPI/database implementation.
- Real provider calls or downloads.
- Browser screenshot evidence.

## Preconditions

- Existing repository context and UI policies read.
- No active requirement existed before this draft task.

## Impact and responsibility

- `IMPACT.md` rows closed: temporary mockup artifact only.
- Existing responsibility extended/replaced/deprecated/removed: none in production.
- New or parallel artifacts and accepted justification: isolated static mockup for
  design review.
- Superseded artifacts assigned to this task: none removed.

## Affected files or components

- `.ai/CURRENT_PLAN.md`
- `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/CHANGE.md`
- `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/IMPACT.md`
- `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/DESIGN_DELTA.md`
- `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/PLAN.md`
- `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/prototype/`

## Acceptance criteria

- [x] Static mockup exists and is isolated from production source.
- [x] Mockup covers the single Provider settings tab.
- [x] Mockup shows overlay feedback and Ollama download state.
- [x] Separate mockup covers Import protocol dates/details, Explorer default/empty
  state and running-job guards.
- [x] Open questions and implementation notes are documented.

## Security Assurance

- Security assurance: not-required: static mockup contains no secrets, no runtime provider calls, no backend connection and no production data.
- Security triggers: future implementation will trigger secrets/network/API/deletion
  review.

## Conditional task annexes

## UI classification

- Design class: 3
- Prototype strategy: isolated-prototype
- Visual review required: no for this static draft; yes before production
  implementation.

## Component impact

### Existing components reused

- App shell, provider cards, tabs, feedback/status styling.

### Existing components extended

- Provider cards and feedback placement in proposed design.

### New shared components

| Name/responsibility | Target path/layer | API/variants/states | Tests | Accessibility | Story/equivalent | Catalog entry |
|---|---|---|---|---|---|---|
| none | not-applicable | not-applicable | not-applicable | not-applicable | not-applicable | not-applicable |

### New feature-local components

- Provider instance card.
- Purpose provider card.
- Add-provider toolbar.
- Ollama download progress block.
- Feedback overlay.

### Components replaced or removed

- Proposed future removal: OpenAI/Ollama LLM free-text fields, separate
  Embedding-/LLM-Provider tabs, active vLLM UI/backend support.

### Rejected reuse options

- Current duplicated connection/model settings tabs.

### Rationale

The static mockup uses existing visual patterns and isolates new IA decisions.

## Prototype relationship

- Prototype artifact:
  `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/prototype/settings-provider-centralization-mockup.html`
- Elements to promote: none directly; reimplement through production architecture
  after approval.
- Prototype-only elements to discard: all inline mock data and CSS.
- Tool dependencies and owning package: none.

## Visual evidence

- Required screens: Provider, overlay feedback, Import protocol, Explorer empty/default,
  running indexing/cluster-set states.
- Required states: default, download, disabled, error.
- Required viewports: desktop/mobile in future browser evidence.
- Manifest: not captured for draft static mockup.

## Implementation constraints

Future production implementation must not reuse prototype code directly as
production architecture.

## Applicable capability specification and test seam

- Specification criteria: `docs/specifications/local-runtime-providers.md`
- Primary observable boundary for this task: static mockup file content.
- Implementation-specific boundaries to avoid testing directly: not applicable.

## Error and recovery implementation

### User actions covered

Static mockup rendering only; no executable user action was changed by this task.

### Expected failures

Not-applicable: this task created isolated design artifacts without runtime API
calls, persistence, provider calls or production UI behavior.

### Unknown failure behavior

- User-facing fallback: not-applicable for static mockup artifacts.
- Correlation ID: not-applicable.
- Retry behavior: not-applicable.
- Input preservation: not-applicable.
- Support behavior: inspect or regenerate the isolated prototype if needed.

### Required negative tests

- [x] not-applicable: runtime user-facing errors are owned by T002-T004.

## Verification

- [x] Focused file inspection
- [x] Relevant linting and static analysis
- [ ] Security or dependency checks when applicable
- [x] Documentation assessment, including `README.md` and `.ai/PROJECT_CONTEXT.md`

Exact commands:

```bash
git diff --check  # passed
node_modules/.bin/playwright-core screenshot --viewport-size=1440,1000 \
  .ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/prototype/settings-provider-centralization-mockup.html \
  /tmp/skm-provider-settings-v2.png  # passed
node_modules/.bin/playwright-core screenshot --viewport-size=390,844 \
  .ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/prototype/settings-provider-centralization-mockup.html \
  /tmp/skm-provider-settings-v2-mobile.png  # passed
node_modules/.bin/playwright-core screenshot --viewport-size=1440,1000 \
  .ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/prototype/project-workflow-adjustments-mockup.html \
  /tmp/skm-project-workflow-adjustments.png  # passed
```

## Risks or blockers

- Production implementation remains blocked by provider instance identity/provenance
  migration.
- Ollama progress percentage may not be simple with the current blocking backend pull.

## Result

Static mockups and draft design/change artifacts created. Production code unchanged.
`git diff --check` and static screenshot rendering passed.

### Adversarial pre-review

- Adversarial pre-review: passed
- Pre-review lenses: UI quality, user-facing errors, security implications for future
  implementation
- Pre-review evidence: static mockup remains isolated; no production source imports;
  no backend connection; open implementation blockers documented in CHANGE and
  DESIGN_DELTA.
- Open P0/P1 findings: none
