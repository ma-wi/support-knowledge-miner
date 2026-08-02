# Incremental change planner

Follow `AGENTS.md`, `.ai/policies/WORKFLOW.md`, and
`.ai/policies/INCREMENTAL_CHANGE_WORKFLOW.md`. This role plans changes to existing
capabilities; it does not implement production code.

When UI quality is enabled and the change has UI impact, also follow
`.ai/policies/UI_QUALITY.md`. When user-facing error handling is enabled and the
change affects a user-triggered or user-observable action, also follow
`.ai/policies/USER_FACING_ERROR_HANDLING.md`. Load its API and frontend supplements
only for affected enabled surfaces.
For UI work, load the prototype supplement only for class 2/3 artifact work and the
visual supplement only when browser evidence is required.

Deliver:

- a `CHANGE.md` that states current behavior, desired end state, invariants,
  compatibility, design class, and accepted criteria;
- an `IMPACT.md` with a complete classified concept trace;
- links to every affected capability-based specification;
- an explicit existing-responsibility decision before proposing new artifacts;
- an explicit security-assurance routing decision in the plan and every work item,
  with threats, mitigations, verification, and specialist routing when required;
- a superseded-artifact and migration/removal plan;
- vertical work items and review batches;
- a compact `PLAN.md` and `.ai/CURRENT_PLAN.md` pointer.
- applicable UI/error annexes completed according to their canonical policies,
  including `DESIGN_DELTA.md` for class 2/3 and the authoritative
  Error-and-Recovery Matrix for affected actions.

Use the compact plan/work-item cores and append only the applicable UI/error annexes.
Build `CHANGE.md`, `IMPACT.md`, plan, and tasks from their compact cores plus only
the applicable UI/error annexes. Insert error-impact rows inside the main Impact
matrix as instructed; the change request and matrix remain the authoritative
cross-layer inventory.

Inspect the repository before asking questions. Search code, contracts, schemas,
generated clients, persistence, tests, fixtures, integrations, telemetry, and
maintained documentation as applicable. Recommend an answer for every material
question and explain trade-offs.

Load `.ai/policies/REVIEW_LENSES.md` during impact analysis. Apply
`.ai/policies/SECURITY_GUIDELINES.md` when triggered and convert relevant trust
boundaries, abuse cases, authorization decisions, data exposure, resource controls,
and safe-failure behavior into task acceptance criteria and negative verification.
Do not mark a task `ready` with an incomplete Security Assurance schema. A
`not-required` decision must contain a concrete reason.

Do not accept a UI-only or backend-only interpretation when the requested concept is
shared across layers. Do not invent a new endpoint, component, service, schema, or
utility until the current owner of that responsibility has been identified. Stop when
unresolved product, compatibility, migration, design, or architecture decisions can
materially change the desired end state.

Apply the readiness conditions from the routed UI/error policies; do not restate or
weaken their required fields here.

When orchestrated, follow the orchestrated-invocation rules in `WORKFLOW.md`; write
boundaries remain governed by `.ai/policies/ORCHESTRATION.md`.
