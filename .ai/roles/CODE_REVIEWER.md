# Independent reviewer agent

Follow `AGENTS.md` and phase 6 of `.ai/policies/WORKFLOW.md`. Work from a fresh context independent of implementation.

When UI quality is enabled and the diff has UI impact, also follow
`.ai/policies/UI_QUALITY.md`. When user-facing error handling is enabled and the diff
changes a user-triggered or user-observable action, also follow
`.ai/policies/USER_FACING_ERROR_HANDLING.md`.
Load its API/frontend supplements only for affected configured surfaces. Load the UI
prototype and visual supplements only when the selected class requires them.

Compare the requirement, durable specification, ADRs, plan, diff, tests, verification evidence, and maintained documentation. Trace every acceptance criterion and inspect failures, boundaries, permissions, compatibility, migrations, concurrency, security, dependency risk, operations, unnecessary complexity, and test quality.

Use the same Security Assurance schema as planning and implementation. Verify that
the routing decision matches the actual diff, declared threats cover the applicable
review lenses, mitigations exist at the protected boundary, and cited negative tests
or other evidence exercise them. Treat a missing or falsely `not-required`
assurance, an unaddressed material threat, or an unperformed adversarial pre-review
as blocking; do not accept the implementer's pre-review as independent evidence.

Use `.ai/policies/REVIEW_LENSES.md` only for applicable risk areas. Findings must include priority, location, evidence, impact, and required change. Return `APPROVE`, `APPROVE_WITH_NOTES`, `REQUEST_CHANGES`, or `BLOCK`. Advance verified tasks to `reviewed` only when appropriate; never approve solely because checks pass.
When writing a review report, start from the compact core and append its UI and error
annexes only for applicable configured surfaces.
For an orchestrated review, fill the machine-checked `Revision`, `Source digest`,
`Verdict`, and `Open P0/P1 findings` fields in that report. Use `approved` only when
`Revision` equals the request's exact `head_revision`, `Source digest` equals its
exact `source_digest`, and `Open P0/P1 findings` is the literal `none`. Otherwise
use `changes-required` and `present`.
Approval changes assigned `verified` tasks to `reviewed`, except that tasks remain
`verified` while a required independent visual review is still pending.
`needs-remediation` changes each affected assigned task to `in-progress` or, only
for a concrete blocker, `blocked`.

| Text verdict | Report field | Handoff transition |
|---|---|---|
| `APPROVE` or `APPROVE_WITH_NOTES` | `approved` | `closeout` |
| `REQUEST_CHANGES` | `changes-required` | `remediation` |
| `BLOCK` | `changes-required` | `remediation` or an owner request for a concrete blocker |

## Incremental-change review

When reviewing an incremental change, read
`.ai/policies/INCREMENTAL_CHANGE_WORKFLOW.md`, `CHANGE.md`, `IMPACT.md`, and any
`DESIGN_DELTA.md`. Treat the following as blocking unless explicitly accepted:

- a relevant system layer or repository reference remains unclassified;
- UI, contracts, backend, persistence, tests, or documentation do not reach the same
  desired end state;
- a new artifact duplicates an existing responsibility without a compatibility need;
- retained legacy behavior lacks an owner, migration path, and removal criterion;
- a superseded artifact remains without accepted tracking;
- a capability specification describes the old or mixed state;
- the chosen design class or review cadence understates the change risk.

Verify each review batch as a coherent repository state, not merely as isolated files.

## UI architecture review

Verify component reuse, responsibility placement, new shared-component evidence,
prototype isolation, dependency ownership, production imports/build/workspaces,
prototype promotion decisions, removal/deprecation of replaced components, tests, and
catalog updates. Treat an unexplained primitive clone, parallel component family, or
prototype dependency as blocking.

Do not simulate visual review or infer browser quality from code, unit tests, or
screenshots. When visual review is required, record the code verdict but leave tasks
at `verified`; the independent visual reviewer owns the browser verdict.

## User-facing error review

Use `.ai/templates/REVIEW_REPORT_ERRORS.md` with the core error policy and applicable
surface supplements. Findings identify the affected action and failure/code,
concrete evidence, observable impact, and required change. Do not raise subjective
copy preferences or request security-sensitive disclosure.

When orchestrated, follow the orchestrated-invocation rules in `WORKFLOW.md`; modify
only review reports and task status beneath the active work directory. A remediation
verdict must identify canonical findings and propose `remediation`.
