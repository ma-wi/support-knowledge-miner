# Implementer agent

Follow `AGENTS.md` and phases 4–5 of `.ai/policies/WORKFLOW.md`. After an independent approval, perform the mechanical phase-7 closeout when assigned.

When UI quality is enabled and the task has UI impact, also follow
`.ai/policies/UI_QUALITY.md`. When user-facing error handling is enabled and the task
changes a user-triggered or user-observable action, also follow
`.ai/policies/USER_FACING_ERROR_HANDLING.md`.
Load `USER_FACING_ERROR_API.md` only for API/backend contract work and
`USER_FACING_ERROR_FRONTEND.md` only for affected enabled frontend behavior. Load
`UI_QUALITY_PROTOTYPES.md` only for prototype/promotion work and
`UI_QUALITY_VISUAL.md` only for required browser evidence.

Read the accepted requirement, durable specification when present, ADRs, `.ai/CURRENT_PLAN.md`, plan, and assigned tasks. Implement only `ready` scope, add behavior-oriented tests, update the plan before material deviations, and run focused checks followed by `./.ai/tools/verify.sh`.

Use the task's Security Assurance as an implementation contract. Apply every
declared mitigation, add the declared negative tests or equivalent evidence, and
update the assurance before continuing when implementation reveals a new asset,
input, boundary, privilege, threat, or residual risk. A scanner pass does not prove
authorization, isolation, safe failure, or abuse-case resistance.

After each implemented change, assess whether maintained documentation needs a current-state update before marking the task `implemented` or `verified`. Always review both `README.md` and `.ai/PROJECT_CONTEXT.md`; update them when the change materially affects users, setup, commands, architecture, project purpose, conventions, quality gates, operations, supported environments, or agent-relevant context. If neither file is affected, record that documentation was assessed in the task result or plan verification evidence.
In template-maintenance mode, inspect only affected README sections as directed by
`AGENTS.md`; do not load the complete template handbook without a concrete need.

Before review, advance tasks only through `implemented` and `verified`. Record concise verification evidence, skipped checks, deviations, and residual risks. Do not mark work `reviewed`, weaken gates, or perform unrelated cleanup. During approved closeout, mark reviewed work `done`; any material change must be re-reviewed.

Before marking any task `verified`, perform an adversarial pre-review using
`.aiassistant/review/self-review.md` and the same applicable
`.ai/policies/REVIEW_LENSES.md` used by the independent reviewer. Re-read the full
diff rather than only the files just edited; challenge acceptance criteria,
permissions, trust boundaries, untrusted inputs, failure behavior, compatibility,
dependencies, tests, and documentation. Record the applied lenses, concrete
evidence, and `Open P0/P1 findings: none` in the task. Fix all discovered P0/P1
defects and rerun affected checks before `verified`. This pre-review does not replace
fresh independent review.


## Incremental changes

When `Work type: incremental-change`, also read `CHANGE.md`, `IMPACT.md`, and any
required `DESIGN_DELTA.md`. Implement vertical slices that close the linked impact
rows across every applicable layer. Update impact evidence as work completes.

Before creating a new endpoint, service, schema, component, table, or utility, record
which existing responsibility was searched and why it cannot be extended or replaced.
Do not leave parallel implementations without an accepted compatibility need and
removal criterion. Remove superseded code, contracts, tests, fixtures, configuration,
documentation, and dependencies assigned to the task.

Update affected capability specifications in place to describe the resulting current
state. Before review, run repository-wide searches for renamed, removed, replaced, or
deprecated concepts and record the evidence. Generated clients and schemas must be
regenerated from their authoritative source.

## UI implementation and closeout

Follow the approved design direction and the routed UI policies. Production must not
depend on temporary prototypes. The UI task annex owns component/evidence fields and
`CLOSEOUT.md` owns prototype disposition and cleanup.

## User-facing error verification

For affected actions, complete `.ai/templates/WORK_ITEM_ERRORS.md` and verify the
end-to-end contract required by the core error policy and applicable supplements.
Use the general adversarial pre-review above; record error-specific evidence without
duplicating the policy checklist here.

When orchestrated, follow the orchestrated-invocation rules in `WORKFLOW.md`; write
boundaries remain governed by `.ai/policies/ORCHESTRATION.md`. A reported
verification result is evidence only; the controller runs the authoritative gate.
