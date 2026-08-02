# Task <task-id>: <title>

- Status: draft | ready | in-progress | blocked | implemented | verified | reviewed | done
- Parent requirement or change:
- Plan:
- Work type: new-capability | incremental-change
- Review batch:
- Depends on:
- Owner/agent:
- Last updated:

## Objective

Describe one independently implementable and verifiable vertical outcome. For an
incremental change, state which impact rows reach their desired end state.

## Scope

### In scope

### Out of scope

## Preconditions

## Impact and responsibility

- `IMPACT.md` rows closed: <!-- manually maintained; verified by the reviewer, not by tooling -->
- Existing responsibility extended/replaced/deprecated/removed:
- New or parallel artifacts and accepted justification:
- Superseded artifacts assigned to this task:

## Affected files or components

## Acceptance criteria

- [ ] <criterion linked to the parent requirement>

## Security Assurance

- Security assurance: required | not-required: <reason>
- Security triggers:
- Assets and data classes:
- Trust boundaries and untrusted inputs:
- Authorization model:
- Threats and abuse cases:
- Mitigations:
- Security verification:
- Residual security risk:
- Specialist security review:

Complete every field when assurance is `required`. Each threat or abuse case must
map to a mitigation and a negative test or other observable evidence. Use
`not-applicable: <reason>` only for individual fields that genuinely do not apply.
When assurance is `not-required`, the routing reason is sufficient.

## Conditional task annexes

Append `.ai/templates/WORK_ITEM_ERRORS.md` when user-facing error handling applies.
Append `.ai/templates/WORK_ITEM_UI.md` only for UI work. The phase-aware validators
require their exact headings when the corresponding configured surface applies.

## Implementation constraints

Include only task-specific constraints. Do not duplicate repository-wide rules.

## Applicable capability specification and test seam

- Specification criteria:
- Primary observable boundary for this task:
- Implementation-specific boundaries to avoid testing directly:

## Verification

- [ ] Focused tests
- [ ] Relevant linting and static analysis
- [ ] Security or dependency checks when applicable
- [ ] Documentation assessment, including `README.md` and `.ai/PROJECT_CONTEXT.md`

Exact commands:

```bash
# Add task-specific commands.
```

## Risks or blockers

## Result

Complete only after implementation. Summarize the resulting state, closed impact
rows, orphan-search evidence, removed or retained superseded artifacts, deviations,
and remaining risks. Do not write a chronological work diary.

### Adversarial pre-review

- Adversarial pre-review: pending | passed
- Pre-review lenses:
- Pre-review evidence:
- Open P0/P1 findings:

Before `verified`, inspect the full diff with `.aiassistant/review/self-review.md` and
the applicable `REVIEW_LENSES.md`, fix all P0/P1 defects found, rerun affected
checks, and record `Open P0/P1 findings: none`.
