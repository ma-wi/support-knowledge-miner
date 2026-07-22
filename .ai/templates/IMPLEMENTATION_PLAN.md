# Implementation plan: <title>

- Status: draft | accepted | in-progress | blocked | completed
- Change class: normal | significant
- Requirement: `docs/requirements/<requirement-id>.md`
- Durable specification: `docs/specifications/<requirement-id>.md` | not-required
- Work directory: `.ai/work/<requirement-id>/`
- Last updated:

## Outcome and implementation boundary

Link to the accepted behavior and summarize only what the implementation must accomplish. Do not duplicate the specification.

- In scope:
- Non-goals:
- Accepted assumptions relevant to implementation:
- Open blockers:

## Current-state findings and approach

- Relevant existing components and test seams:
- Proposed implementation:
- Alternatives rejected for implementation reasons:

## Affected areas

- Components and interfaces:
- Data and migrations:
- Dependencies and configuration:
- Deployment and operations:
- Documentation:

## Risks and recovery

- Security/privacy:
- Compatibility/migration:
- Performance/reliability:
- Rollback/recovery:

## Work items

Create separate files only for independently implementable, assignable, blockable, or verifiable units.

| ID | Outcome | Status | Depends on | Task file |
|---|---|---|---|---|
| T001 | | ready | none | `tasks/T001-<slug>.md` |

## Acceptance-criteria traceability

| Criterion in durable requirement/specification | Work item | Automated verification |
|---|---|---|
| AC-1 | T001 | |

## Verification and closeout

- Focused commands:
- Full command: `./.ai/tools/verify.sh`
- Specialist review required and why:
- Durable documentation/ADR updates, including `README.md` and `.ai/PROJECT_CONTEXT.md` assessment:
- Temporary artifacts to remove after review:

## Material deviations

Record only deviations that change scope, risk, interfaces, migration, test seams, or verification.
