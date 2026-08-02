# Implementation plan: <title>

- Status: draft | accepted | in-progress | blocked | completed
- Change class: normal | significant
- Work type: new-capability | incremental-change
- Requirement: `docs/requirements/<requirement-or-change-id>.md`
- Change request: `.ai/work/<change-id>/CHANGE.md` | not-applicable
- Change impact: `.ai/work/<change-id>/IMPACT.md` | not-applicable
- Canonical capability specifications: `docs/specifications/<capability-slug>.md` | not-required
- Work directory: `.ai/work/<requirement-or-change-id>/`
- Last updated:

## Outcome and implementation boundary

Link to the accepted behavior and summarize only what the implementation must accomplish. Do not duplicate the specification.

- In scope:
- Non-goals:
- Accepted assumptions relevant to implementation:
- Open blockers:

## Current-state findings and approach

- Relevant existing responsibilities, components, contracts, and test seams:
- Desired end state implemented by this plan:
- Existing responsibility to extend/replace/deprecate/remove:
- Proposed implementation:
- New or parallel artifacts and accepted justification:
- Alternatives rejected for implementation reasons:

## Affected areas

- Components and interfaces:
- Data and migrations:
- Dependencies and configuration:
- Deployment and operations:
- Documentation:

## Conditional plan annexes

Append `.ai/templates/IMPLEMENTATION_PLAN_UI.md` only when UI quality applies.
Append `.ai/templates/IMPLEMENTATION_PLAN_ERRORS.md` only when user-facing error
handling applies. For incremental work, the annexes summarize and link to
`CHANGE.md`, which remains authoritative.

## Risks and recovery

- Compatibility/migration:
- Performance/reliability:
- Rollback/recovery:

## Security Assurance routing

- Security assurance: required | not-required: <reason>
- Security triggers: <data, identity, files, network, commands, parsing, secrets,
  public/admin API, dependency/build chain, irreversible change, or none with reason>
- Threat model: `.ai/work/<id>/THREAT_MODEL.md` | not-required: <reason>
- Specialist security review: required: <scope/timing> | not-required: <reason>

When assurance is required, every affected work item completes the shared Security
Assurance schema before it becomes `ready`. Link threats to mitigations and negative
tests or other observable evidence; do not rely on a scanner result alone.

## Review cadence

- Cadence: per-task | batch | feature
- Maximum tasks per review batch:
- Forced per-task review triggers present:
- Rationale:

## Work items

Prefer vertical, end-to-end slices. Create separate files only for independently
implementable, assignable, blockable, or verifiable outcomes.

| ID | Vertical outcome | Status | Depends on | Review batch | Impact rows closed | Task file |
|---|---|---|---|---|---|---|
| T001 | | ready | none | RB001 | | `tasks/T001-<slug>.md` |

## Acceptance-criteria traceability

| Criterion in durable requirement/specification | Work item | Automated verification |
|---|---|---|
| AC-1 | T001 | |

## Superseded-artifact and canonical-spec closeout

- Superseded artifacts assigned for removal/deprecation:
- Repository-wide orphan searches required:
- Capability specifications to update in place:
- Temporary compatibility behavior and removal criteria:

## Verification and closeout

- Focused commands:
- Full command: `./.ai/tools/verify.sh`
- Specialist review required and why:
- Durable documentation/ADR updates, including `README.md` and `.ai/PROJECT_CONTEXT.md` assessment:
- Temporary artifacts to remove after review:

## Material deviations

Record only deviations that change scope, risk, interfaces, migration, test seams, or verification.
