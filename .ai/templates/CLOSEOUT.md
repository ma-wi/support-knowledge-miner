# Closeout: <requirement or change>

- Work ID:
- Status: draft | ready | completed
- Requirement or change:
- Reviewed production revision:
- Code-review status:
- Visual review required: yes | no
- Visual-review status: approved | changes_requested | requires_human_decision | invalid_review | not-required
- Last updated:

## Prototype-element decisions

Use exactly one disposition per element: `promoted`, `reimplemented`, `discarded`,
`retained-as-maintained-story`, or `retained-as-permanent-design-reference`.

| Element or artifact | Disposition | Production target or permanent location | Owner | Purpose and isolation/cleanup evidence |
|---|---|---|---|---|
| none | discarded | not-applicable | not-applicable | no prototype used |

## Isolated prototype cleanup

- Prototype directory: not-applicable
- Removed: yes | no | not-applicable
- Package manifest and lockfile removed: yes | no | not-applicable
- Build output removed: yes | no | not-applicable
- Production imports rechecked: yes | no | not-applicable
- Workspace/runtime dependencies rechecked: yes | no | not-applicable

## Storybook prototype cleanup

- Prototype stories:
- Deleted or converted to maintained stories:
- Prototype markers removed from maintained stories: yes | no | not-applicable
- Catalog or story inventory updated: yes | no | not-applicable

## Durable current-state updates

- [ ] Affected capability specifications describe current truth.
- [ ] Error Catalog describes current active and deprecated codes.
- [ ] Removed codes, frontend mappings, duplicate mappers, generic known-error
  messages, dead fixtures, and dead tests were removed.
- [ ] Error documentation has no contradictory current-state descriptions.
- [ ] `docs/design/DESIGN_SYSTEM.md` was updated or assessed as not affected.
- [ ] `docs/design/COMPONENT_CATALOG.md` was updated or assessed as not affected.
- [ ] Replaced or deprecated components have an owner and removal criterion.
- [ ] README and project context were assessed.

## Temporary visual evidence

- Evidence policy: delete | retain
- Evidence removed:
- Retention purpose and owner, when retained:

## Final verification

- Commands and results:
- Skipped checks and reasons:
- Residual limitations:
- Ready to remove temporary work: yes | no
