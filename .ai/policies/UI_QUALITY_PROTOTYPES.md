# UI prototypes and controlled promotion

Load this supplement for class 2/3 design artifacts, Storybook compositions, isolated
prototypes, or prototype promotion. Also follow `UI_QUALITY.md`.

## Supported artifacts and tooling

Configured artifact types may include `static-mockup`,
`clickable-html-prototype`, `react-mock-prototype`, `storybook-composition`, and
`external-design-reference`. An allowed type does not install its tooling.

- Durable tooling is an exact, locked development dependency in its owning frontend
  package.
- Prototype-only dependencies stay in the private isolated prototype package.
- External tools require a reproducible procedure and concrete revision reference.

## Isolated prototypes

The default location is `.ai/work/<change-id>/prototype/`. It is temporary, private,
non-publishable, non-deployable, outside production source, and excluded from
production build, routing, workspaces, module resolution, and runtime dependencies.
It uses mock data/local fixtures only and never connects to production services,
configuration, secrets, or data.

Its README states that it is not production code. If it has `package.json`, the
package is private, its name ends in `-design-prototype`, and it has its own lockfile.

An optional worktree is permitted for class 3 experiments; the same isolation rules
apply.

## Storybook compositions

A temporary composition may import existing production components with mock data. It
is marked `prototype-only: <change-id>`, unreachable through production routes, free
of production side effects, and deleted or converted into a maintained story during
closeout. Conversion removes the marker and updates the catalog/story inventory.

## Controlled promotion

Classify each relevant element as:

```text
reuse-existing-production-component
extend-existing-production-component
create-design-system-component
create-feature-local-component
implement-page-composition
discard-prototype-only-code
```

Record target path/layer, responsibility, tests, story, accessibility, and catalog
impact. Reimplement through production architecture. Never promote mock data, stubs,
hard-coded styles, temporary state, prototype API calls, experimental dependencies,
duplicate components, untyped/static data, provisional accessibility, or prototype
routes unchanged.

## Closeout

Use exactly one disposition per element: `promoted`, `reimplemented`, `discarded`,
`retained-as-maintained-story`, or `retained-as-permanent-design-reference`.

Delete isolated prototypes by default, including manifests, lockfiles, and build
output. `discarded`, `promoted`, or `reimplemented` is invalid while the temporary
prototype remains. A permanent reference needs purpose, owner, documented location,
and continuing build/dependency isolation.
