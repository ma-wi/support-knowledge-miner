# Incremental change workflow

Use this policy when changing, extending, replacing, renaming, deprecating, or
removing behavior in an existing capability. It supplements the canonical lifecycle
in `WORKFLOW.md`; that file still owns status transitions and closeout.

When `.ai/project.yaml` enables UI quality and the change has UI impact, also follow
`.ai/policies/UI_QUALITY.md`. When it enables user-facing error handling and the
change affects a user-triggered or user-observable action, also follow
`.ai/policies/USER_FACING_ERROR_HANDLING.md`. Record concrete not-applicable routing
reasons without loading those policies for unaffected work.

## Goal

End with one coherent current system, not a new implementation beside an unexplained
legacy implementation. Every incremental change must define the current state, the
desired end state, affected responsibilities, migration or compatibility needs, and
what becomes obsolete.

## Canonical capability specifications

Durable specifications are capability-based current-state documents:

```text
docs/specifications/<capability-slug>.md
```

Examples:

```text
docs/specifications/customer-management.md
docs/specifications/authentication.md
docs/specifications/reporting.md
```

A capability specification describes what is true after accepted changes. Update it
in place during an incremental change. Do not create a chain of change-specific specs
that an agent must reconstruct to understand current behavior. Git and pull requests
retain history.

A change may affect multiple capability specifications. List every affected canonical
specification in the change request and plan. If no observable capability contract is
affected, record `not-required` with a reason.

## Required temporary artifacts

Normal or significant incremental changes use:

```text
.ai/work/<change-id>/
├── CHANGE.md
├── IMPACT.md
├── DESIGN_DELTA.md       # only for design class 2 or 3
├── PLAN.md
└── tasks/
```

Create `CHANGE.md` from `.ai/templates/CHANGE_REQUEST.md` and `IMPACT.md` from
`.ai/templates/CHANGE_IMPACT.md`. These artifacts remain temporary and are removed
after closeout, after durable specifications and maintained documentation reflect the
new current state.

## 1. Establish current and desired state

Before planning implementation:

1. identify the existing owner of the behavior or responsibility;
2. trace the concept through relevant layers and integrations;
3. describe the current observable behavior;
4. define one unambiguous desired end state;
5. identify invariants that must remain true;
6. decide compatibility, migration, deprecation, and removal behavior;
7. obtain acceptance from the named decision owner.

Do not plan from the requested UI symptom alone. A request such as “remove this field”
requires a repository-wide concept trace unless the requester explicitly limits the
scope and accepts the resulting retained behavior.

## 2. Complete the change-impact matrix

Classify every relevant located artifact or responsibility with exactly one action:

```text
keep
modify
migrate
deprecate
remove
replace
not-applicable
```

Typical layers include:

- user interface and interaction state;
- frontend validation, feature models, and generated API client;
- public API contracts and compatibility surface;
- backend request/response schemas and application services;
- domain model and business rules;
- persistence, migrations, jobs, and data lifecycle;
- integrations, events, caches, search, and telemetry;
- tests, fixtures, documentation, and operational tooling.

When user-facing error handling applies, insert the rows from
`.ai/templates/CHANGE_IMPACT_ERRORS.md` and follow the core error policy instead of
duplicating its layer checklist here.

The matrix may omit an irrelevant layer only when its absence was verified and noted.
No relevant located reference may remain unclassified before implementation.

## 3. Existing responsibility and no-parallel-implementation rule

Before adding a new endpoint, service, component, schema, table, utility, or workflow:

1. search for the existing owner of the same responsibility;
2. choose to extend, replace, deprecate, or remove it;
3. document why a new artifact is necessary;
4. when parallel behavior is required, define compatibility need, owner, migration
   path, and removal criterion.

A parallel implementation is forbidden when the only rationale is that adding a new
artifact is easier than changing the current one.

## 4. Superseded-artifact plan

Maintain a list in `IMPACT.md` for code, endpoints, schemas, components, tests,
configuration, documentation, and dependencies made obsolete by the change. Each
entry needs a disposition and an owning task. An artifact may remain only for an
accepted compatibility reason with a concrete removal criterion.

## 5. Design routing

When UI quality is enabled and the change has UI impact, use
`.ai/policies/UI_QUALITY.md` as the canonical owner of design classes, readiness,
component reuse, evidence, and classification integrity. Record class 0 with a
concrete reason for unaffected work without loading the detailed UI policy.

## 6. Vertical work items

Prefer work items that deliver a coherent end-to-end behavior slice across all
applicable layers. Avoid separate backend, API, frontend, test, and documentation
items that leave the system inconsistent between tasks.

A larger change may use staged vertical slices, for example:

1. introduce a compatible contract and migration;
2. switch active behavior end-to-end;
3. remove legacy behavior and superseded artifacts.

Every task links to the impact rows and acceptance criteria it closes.

Each changed user action links to its authoritative Error-and-Recovery Matrix. The
core error policy owns its readiness conditions.

## 7. Review cadence and batches

The plan selects one cadence:

- `per-task`: review each task independently;
- `batch`: review a small coherent set of tasks together;
- `feature`: review after the whole small change is verified.

Use the defaults in `.ai/project.yaml`. Force `per-task` review for triggers configured
there, including migrations, public contracts, authentication, authorization,
security-sensitive work, and dependency changes unless the decision owner explicitly
requires an even stricter boundary. Do not exceed the configured maximum batch size.

A review batch must be coherent and leave the repository in a verifiable state. A
batch is not permission to postpone tests or hide incompatible intermediate states.

## 8. Implementation and evidence

The implementer updates impact rows and superseded-artifact entries with concrete
verification evidence. The canonical capability specifications are updated to the
accepted new state in the same change. Do not append a chronological delta to a
current-state spec.

Before review, perform repository-wide searches for renamed, removed, replaced, or
deprecated concepts and record the result. Generated artifacts must be regenerated
from their source contract rather than edited manually.

For affected work with UI quality enabled, each task completes the component-reuse
search and required `Component impact` sections. Selected design/browser tooling must
be installed and locked in its owning development package before use. Prototype-only
packages stay private and outside production workspaces.

## 9. Independent review

The reviewer must determine whether:

- the desired end state is implemented across every applicable layer;
- no relevant impact row is missing or unsupported by evidence;
- existing responsibility was adapted instead of unnecessarily duplicated;
- retained legacy behavior has an accepted compatibility reason and removal plan;
- superseded artifacts were removed or explicitly tracked;
- capability specifications describe the resulting current state;
- when user-facing error handling applies, the error catalog and applicable layers
  describe one consistent current state;
- when UI quality applies, design classification and required evidence are valid;
- when UI quality applies, production has no prototype dependency;
- when UI quality applies, component reuse, design approval, revision-bound evidence,
  and independent visual review satisfy the selected class;
- vertical slices and review cadence did not hide integration defects.

Unexplained orphan references, parallel implementations, stale canonical specs, or
missing removal work are blocking findings.

## 10. Closeout

Before deleting temporary change artifacts:

1. update every affected capability specification to current truth;
2. update maintained project, architecture, design, operations, and user documentation;
3. verify that superseded artifacts are removed or have accepted tracked removal work;
4. remove or deprecate obsolete error codes, mappings, generic known-error messages,
   duplicate mappers, dead fixtures/tests, and contradictory error documentation;
5. move only genuine future work to issues or `.ai/NEXT_STEPS.md`;
6. run final repository-wide orphan searches and `./.ai/tools/verify.sh`;
7. remove `CHANGE.md`, `IMPACT.md`, optional `DESIGN_DELTA.md`, plan, and tasks;
8. reset `.ai/CURRENT_PLAN.md`.

Before removal, classify and clean every isolated or Storybook prototype, update
`docs/design/DESIGN_SYSTEM.md` and `docs/design/COMPONENT_CATALOG.md` where required,
and apply the temporary visual-evidence retention policy.

The pull request and Git history retain the change history. Durable specifications
retain only the accepted current state.
