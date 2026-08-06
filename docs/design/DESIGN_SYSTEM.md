# Design system

This document describes current visual and interaction rules for the local React
application. It is not a change log.

## Foundations

- Target audience: analyst/curator working through local imported support data.
- Product character: pragmatic, dense, local-first analysis workspace.
- Design goals: make project state, background jobs, Cluster-Set lineage, source
  evidence and export state explicit without decorative noise.
- Expected information density: medium-high on desktop, single-column and
  stack-first on mobile.
- Primary component foundation: project-local React components with CSS in
  `frontend/src/App.css`; no external component library.
- Styling strategy: semantic CSS custom properties in `:root`, feature-local
  classes for compositions, no inline tokens except documented tree indentation.
- Icon strategy: text labels first; inline SVG only where an action needs a compact
  secondary affordance.
- Supported display modes: light mode, desktop `1440x1000`, mobile `390x844`.

Additional component libraries require a documented responsibility, compatibility
reason and removal strategy.

## Design tokens

- Semantic colors: `--text #172033`, `--muted #64748b`, `--cyan #0e7490`,
  `--amber #d97706`, `--emerald #16a34a`, `--danger #dc2626`.
- Surface colors: `--bg #f6f9fb`, `--bg-soft #edf5f8`, `--panel #ffffff`,
  `--panel-strong #f8fbfc`, `--light #ffffff`.
- Status colors: success uses emerald on light green; info uses cyan on light cyan;
  warning uses amber/orange; errors use danger red.
- Typography: Inter/system UI stack; headings use heavy weights and clear hierarchy.
- Font sizes: inherited browser base with larger page headings; small captions use
  compact uppercase/letter-spaced styling.
- Font weights: controls and chips are bold; table group rows use extra-bold.
- Line heights: prose and hints use comfortable multiline spacing.
- Spacing: panels use `clamp()` padding; grids use roughly `0.8rem` to `1.25rem`
  gaps.
- Radii: controls `14px`, cards/sections `16px`, large panels `--radius 20px`.
- Shadows: one soft panel shadow `--shadow`.
- Z-index conventions: dialogs use `z-index: 30`; global feedback overlays use
  `z-index: 50`; avoid other new stacking contexts.
- Animation and motion conventions: hover elevation is minimal; browser evidence
  disables animations; no required motion for comprehension.

## Layout

- Grid: page/workspace grids on desktop; `panel-grid`, settings/provider grids and
  Explorer layout collapse to one column below `980px`.
- Maximum content widths: auth card is constrained; workspace fills available app
  shell width.
- Page padding: responsive clamp-based app shell padding.
- Form widths: forms use full available panel width with stacked labels.
- Breakpoints: primary responsive breakpoint `980px`; mobile stacks metrics and
  actions.
- Desktop behavior: signed-in pages use the top-right menu for global navigation;
  no persistent left global sidebar is present. The Explorer workspace adds a left
  control rail for Explorer-only controls while the table remains the main
  workspace.
- Mobile behavior: project tabs wrap, Explorer rail/table stack, wide tables scroll
  horizontally inside bordered containers.
- Scroll and sticky behavior: tables scroll within `.cluster-table-wrap`; dialogs
  scroll internally with bounded viewport height.

## Component rules

### Buttons and actions

Primary buttons use cyan fill and white text. Secondary buttons use the established
`secondary` variant. Destructive actions use the `danger` variant. Disabled actions
must stay visible with reduced opacity and keep explanatory surrounding text.

### Forms and field groups

Labels wrap their controls. Cloud-provider confirmations are explicit checkbox
fields. Write-only secrets never render saved values. Failed actions preserve safe
input where practical.

### Feedback

Global feedback/status messages render as fixed overlays outside the content flow
so page content does not shift. They retain the established success/info/warning
and error styling, include a manual close action and auto-dismiss when appropriate.

### Tables and lists

Use tables for analyst comparison across Cluster rows. Tables keep left-aligned
headers, visible row separators and horizontal scroll on small screens. List/card
layouts are acceptable for projects, users, imports, jobs and Cluster-Set tree
nodes.

### Navigation

Primary app navigation is opened from a top-right three-bar menu with exactly
Projekte, Einstellungen and Abmelden. No signed-in view renders a persistent left
global sidebar. Project workflow tabs are: Import, Indizieren, Cluster-Sets,
Explorer and Projekt löschen. Removed Profile, Runs, Kandidaten and separate
Export tabs must not be reintroduced without an accepted requirement.

### Dialogs and drawers

Source and Summary-regeneration dialogs use modal semantics with `role="dialog"`
and `aria-modal="true"`.
They focus the close button on open, trap Tab/Shift+Tab inside the dialog, close by
button or Escape, and return focus to the opener.

### Cards

Cards show a strong title, compact metadata, status/progress when applicable and
only state-valid actions.

### Feedback messages

Feedback messages use `role="status"` for non-errors and `role="alert"` for
errors. Error messages must be safe, actionable and catalogued when user-facing.

### Loading states

Loading text must appear at the affected surface and avoid false success.
Background jobs show status, phase, progress and safe diagnostics.

### Empty states

Empty states explain the missing prerequisite or recovery action, e.g. create an
import, run indexing, generate a Cluster-Set, select a completed set or adjust
Explorer filters.

### Error states

Field, form, component and page errors follow
`.ai/policies/USER_FACING_ERROR_HANDLING.md`. Do not expose secrets, raw provider
bodies, SQL, stack traces or unnecessary raw support text.

### Validation states

Use native form constraints where sufficient and safe frontend guards where the
backend has a catalogued business rule.

### Confirmation and destructive actions

Deletion and cloud text transfer require explicit user action. Production access is
not a supported UI state.

## Accessibility

- Focus appearance: visible focus outline on controls.
- Keyboard operation: tabs, forms, tables, dialogs and source inspection are
  keyboard reachable.
- Labels and accessible names: every input/select/button has visible text or an
  explicit accessible label.
- Error-message association: errors appear in alert/status regions near the
  affected workflow.
- Contrast: use the documented semantic colors on light surfaces.
- Semantic structure: page headings, regions, forms, tables and dialogs use roles
  that match their purpose.
- Screen-reader requirements: status changes are announced and table/dialog labels
  are descriptive.
- Reduced motion: no workflow depends on motion.

## Governance

- Allowed deviations: feature-local composition classes when no shared component
  exists.
- Forbidden deviations: parallel Candidate/Export workflows, hidden raw-text
  export, unlabeled controls, non-modal source dialog behavior.
- New-component process: search this file, the component catalog, shared app code
  and feature-local variants before adding a new component.
- New-token process: prefer existing semantic tokens; new hard-coded colors require
  design-system update in the same change.
- Design-class-3 process: approved design delta, browser evidence, accessibility,
  visual-regression and independent visual review are required.
- Required approvals: human approval for class 2/3 direction before production
  implementation.
- Deprecated-pattern handling: remove obsolete UI paths or mark them deprecated
  with a replacement and removal criterion in the component catalog.
