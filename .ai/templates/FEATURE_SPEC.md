# Capability specification: <capability>

Store accepted current-state specifications at
`docs/specifications/<capability-slug>.md`. Update this document in place when the
capability changes; Git and pull requests retain history. Do not append a chronological
change log or create a specification chain for each incremental request.

- Capability ID or slug:
- Source requirements or change requests:
- Status: draft | needs-clarification | awaiting-confirmation | accepted | ready-for-implementation | superseded
- Discovery artifact, if used:
- Decision owner:
- Last updated:

## Purpose and responsibility

Describe the durable responsibility, affected users or systems, and current observable
outcome. Keep this independent of temporary implementation details.

## Current state and terminology

- Applicable ADRs:
- Existing domain terms and definitions:
- Current accepted behavior or constraints:
- Current owners across UI, contracts, backend, data, and integrations:
- Terminology conflicts to resolve:

Use established project and domain terminology. Do not introduce synonyms for existing concepts without a documented reason.

## Scope

### In scope

-

### Out of scope / non-goals

-

## User-visible behavior

Describe workflows, state transitions, permissions, failures, and recovery behavior. Use user stories only where actor, goal, and value add clarity.

### Optional user stories or journey scenarios

| ID | Actor | Trigger or goal | Expected outcome | Related criteria |
|---|---|---|---|---|
| US-1 | | | | AC-1 |

## Functional requirements

- FR-1:

## Quality and operational requirements

- Security and privacy:
- Reliability and recovery:
- Performance and capacity:
- Accessibility and UX:
- Compatibility and migration:
- Observability and support:

## Interfaces, data, and domain rules

- Public interfaces and contracts:
- Data ownership and lifecycle:
- Validation and authorization rules:
- External integrations:

## Test seams and verification decisions

Identify the smallest useful set of stable, observable boundaries through which behavior should be verified.

### Primary test seam

- Boundary:
- Behaviors covered:
- Why this is stable and representative:

### Secondary seams, only where necessary

-

### Seams deliberately avoided

Examples: private helpers, internal component state, ORM details, or other implementation-specific boundaries.

-

## Acceptance criteria

- [ ] AC-1:

## Decisions and accepted assumptions

### Confirmed decisions

-

### Accepted assumptions

-

### Rejected alternatives that matter later

-

## Superseded behavior and active deprecations

List only accepted temporary compatibility behavior that still exists, including owner
and removal criterion. Use `none` when the capability has no active deprecation.

-

## Open questions and blockers

-

## External standards references

Record only source identifiers and adopted conclusions. Do not copy large retrieved passages.

-

## Readiness decision

The implementation agent may begin only when:

- material scope and behavior decisions are resolved;
- acceptance criteria are testable;
- test seams are defined;
- remaining assumptions are explicit and acceptable;
- the user or decision owner has confirmed the specification where required.

- Shared understanding confirmed: yes | no | not-required
- Confirmed by:
- Confirmation date:
- Ready for implementation: yes | no
- Readiness conditions or remaining blockers:

Set `Status: ready-for-implementation` only when `Ready for implementation: yes`.
