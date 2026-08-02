# UI quality

Load this policy only when `.ai/project.yaml` declares `ui_quality.enabled: true`
and the work has user-interface impact. For unaffected work, record class 0 with a
concrete reason in the plan's UI routing annex without loading this policy. When
disabled, it creates no design,
prototype, browser, accessibility, or visual-review obligation. It extends the
canonical workflow rather than adding statuses.

Load supplements only when their surface applies:

| Trigger | Additional policy |
|---|---|
| A class 2 or 3 change uses a mockup, Storybook composition, prototype, or promotion | `UI_QUALITY_PROTOTYPES.md` |
| Design class 1–3 requires browser evidence or visual review | `UI_QUALITY_VISUAL.md` |
| User-facing error states change | Core error policy and configured error supplements |

## Canonical sources

- Current design rules: `docs/design/DESIGN_SYSTEM.md`
- Reusable component inventory: `docs/design/COMPONENT_CATALOG.md`
- Temporary class 2/3 direction: `.ai/work/<id>/DESIGN_DELTA.md`

The production frontend is the only source of shipped UI code. Design-system
documents describe current truth, not history.

## Design classes

### Class 0 — no visual change

Backend-only, internal, data, performance, or behavior-neutral work with no
observable UI effect. No design artifact, screenshot, or visual review.

### Class 1 — established pattern

Use only when an existing component plus interaction/layout pattern is reused without
a new visual direction or component family. Record reused components, the applicable
design-system rule, and component impact; implement directly; then produce
revision-bound screenshots and simplified independent visual review.

An isolated prototype, new shared component family, cross-cutting standard, or
substantially new flow requires a higher class.

### Class 2 — new composition or flow

Use for new dialogs, pages, dashboards, multi-step flows, materially different
states, or new compositions. Require:

- approved `DESIGN_DELTA.md` with flow, screens/states, responsive behavior,
  component/design-system impact, accessibility, and relevant error states;
- a permitted concrete design artifact;
- explicit reuse/extend/create decisions;
- approval before production implementation;
- full revision-bound browser evidence and independent visual review.

### Class 3 — new design or interaction standard

Use for navigation, layout standards, component families, information architecture,
responsive strategy, form concepts, tokens, or component-foundation changes. Meet
class 2 plus:

- isolated prototype by default;
- explicit human approval;
- recorded change-base Git revision;
- updates to both maintained design sources;
- token, accessibility, responsive, migration, and regression impact;
- migration/removal plan for affected screens and components.

## Classification integrity

The parent artifact records current, highest assigned, and implementation-start
classes. Raising the class is always permitted with history. After implementation
starts, lowering below either recorded class is forbidden. Class 2/3 implementation
requires `DESIGN_DELTA.md` with `Status: approved`.

## Component reuse and impact

Before creating a component, search design-system primitives/forms/layout/feedback,
the Component Catalog, shared application components, affected feature-local
components, and existing variants/extensions.

Every UI task records:

```markdown
## Component impact
### Existing components reused
### Existing components extended
### New shared components
### New feature-local components
### Components replaced or removed
### Rejected reuse options
### Rationale
```

New shared components require one responsibility, documented API, relevant states,
tests, accessibility and visual evidence, a maintained story/equivalent, and a
catalog entry. Feature-local components require a domain responsibility, locality
rationale, tests, relevant states, and recorded shared-component search.

Repeated primitive forms, label/error logic, dialog/table structures, hard-coded
tokens, or local clones of standard components are blocking reuse findings.

## Design readiness and closeout

Selected tooling must be installed in its owning package with an exact or bounded
version requirement and an adjacent lockfile whose exact resolution satisfies that
requirement before its gate can pass. Missing tooling is not a successful skip.

During closeout, update maintained design sources and capability specifications,
classify every temporary artifact, remove or deliberately promote it according to
`UI_QUALITY_PROTOTYPES.md`, and apply the evidence retention rules in
`UI_QUALITY_VISUAL.md`. Material closeout changes return to review.

Static checks validate fields, paths, isolation links, stale evidence, and
classification. They cannot prove visual quality, accessibility, interaction
coverage, human identity, or absence of indirect runtime connections.
