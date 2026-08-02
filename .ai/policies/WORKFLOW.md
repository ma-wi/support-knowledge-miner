# Canonical agent workflow

This file owns lifecycle and status transitions; role files add only role-specific
responsibilities. Use one active requirement or change per branch/worktree.

```text
planner → implementer → independent reviewer
                    ↖ remediation ↙
                 mechanical closeout
```

When `.ai/project.yaml` enables repository-native orchestration,
`.ai/policies/ORCHESTRATION.md` controls queueing, isolated invocations, owner gates,
resume, and transition validation around this same lifecycle. It does not add task
statuses or replace canonical artifacts. Manual role handoff remains supported when
orchestration is absent or disabled.

When UI quality is enabled and the work has UI impact, design approval precedes
implementation for design classes 2 and 3, and required visual review follows
technical verification and code review. `.ai/policies/UI_QUALITY.md` owns the
detailed UI gates.

When user-facing error handling is enabled and an affected action is user-triggered
or user-observable, `.ai/policies/USER_FACING_ERROR_HANDLING.md` adds one
error-contract readiness and verification lens to this lifecycle. It does not add
statuses or a parallel workflow.

Testing, security, dependencies, and documentation are conditional review lenses.
Use a specialist context only for significant risk or an explicit requirement.
Trivial work uses the reduced path in `AGENTS.md`: no temporary work directory, only
the relevant focused checks during work, full `verify.sh` before merge or PR, and no
planner/implementer/reviewer split unless risk demands it.

## Default baseline

- Use the `trivial`, `normal`, or `significant` classification defined in `AGENTS.md`;
  when unsure, choose the higher class.
- Keep one active requirement or change per branch or worktree.
- Do not start implementation until required specifications, ADRs, and task files are ready.
- Finish normal/significant work with `./.ai/tools/verify.sh`.
- For trivial work, run focused relevant checks and full `verify.sh` before merge.
- Never claim an unobserved pass.

## 1. Intake and classification

The planner reads the requirement, configuration, context, applicable ADRs, and
relevant code/tests. Record the `trivial`, `normal`, or `significant` class defined in
`AGENTS.md`; material uncertainty raises the class.

## 2. Discovery and durable specification

For significant or materially unclear work, create
`.ai/work/<requirement-or-change-id>/DISCOVERY.md` from
`.ai/templates/FEATURE_DISCOVERY.md`. Resolve only decisions that can change outcome,
scope, behavior, risk, architecture, or acceptance criteria, then obtain explicit
shared-understanding confirmation.

Store significant specifications as capability-based current-state documents at
`docs/specifications/<capability-slug>.md`. They own observable behavior, scope,
accepted decisions, criteria, and stable test seams for one durable capability.
Incremental changes update affected capability specifications in place rather than
creating change-specific specification chains.
Agents propose requirements, specifications, and ADRs; a named authorized decision
owner records acceptance. Dependent implementation waits for accepted ADRs and:

```text
Status: ready-for-implementation
Ready for implementation: yes
```

## 3. Temporary planning

When changing an existing capability, first follow
`.ai/policies/INCREMENTAL_CHANGE_WORKFLOW.md`. Create accepted `CHANGE.md` and
`IMPACT.md`, classify design impact, identify existing responsibility and superseded
artifacts, then plan vertical work items and review batches.

Normal/significant work uses:

```text
.ai/work/<requirement-or-change-id>/
├── DISCOVERY.md           # only when needed
├── CHANGE.md              # incremental changes only
├── IMPACT.md              # incremental changes only
├── DESIGN_DELTA.md        # incremental design class 2 or 3 only
├── PLAN.md
├── tasks/                 # vertical independently verifiable units
├── evidence/ui/           # temporary, only when visual evidence is required
└── CLOSEOUT.md            # UI-artifact closeout when needed
```

The plan links to durable inputs and records approach, sequence, affected areas,
risks, verification, migration/recovery, and documentation. Create or update
`.ai/CURRENT_PLAN.md` from `.ai/templates/CURRENT_PLAN.md`. Planner task statuses are
`draft` or `ready`.

The planner loads `REVIEW_LENSES.md` and records Security Assurance routing in the
plan and every work item. A task with a triggered security threat surface cannot
become `ready` until its assets, data classes, trust boundaries, untrusted inputs,
authorization model, threats/abuse cases, mitigations, negative verification,
residual risk, and specialist-review decision are complete. A task without a
trigger records a concrete `not-required` reason.

Before a user-facing task becomes `ready`, every changed user action has a complete
Error-and-Recovery Matrix, catalog/contract impact, negative-test strategy, and
explicit `not-applicable` rationale for irrelevant categories.

## 4. Implementation

The implementer takes a `ready` task, marks it `in-progress`, and implements the
smallest coherent behavior slice with tests. Incremental tasks must close their linked
impact rows end-to-end and may not leave unexplained parallel or superseded behavior. Record material deviations before
continuing. After code/tests are complete mark `implemented`; after focused checks
pass mark `verified`.

Before `verified`, the implementer performs the adversarial pre-review defined by
the role, applies the same relevant review lenses as the independent reviewer, fixes
all P0/P1 defects found, reruns affected checks, and records lenses and evidence in
the work item. Automated gates supplement but do not replace this semantic review.

For UI design classes 2 and 3, implementation may start only after
`DESIGN_DELTA.md` is approved. Production code may never import, build, route to, or
depend on a temporary prototype.

## 5. Full verification

Run `./.ai/tools/verify.sh`. It runs locked setup for configured projects, then every
configured mandatory gate. Every mandatory gate must execute and pass; a mandatory
skip fails. Record exact commands/results and environment limitations.

The error-handling gate is phase-aware: draft discovery may be incomplete, while
Readiness, Verify, Review, and Closeout enforce the configured contract, catalog,
mapping, recovery, negative-test, and evidence requirements.

## 6. Independent review and remediation

A fresh reviewer context compares requirement, capability specifications, ADRs, plan,
full diff, tests, verification, and affected documentation. For incremental work it
also validates the desired end state, impact matrix, existing-responsibility decision,
superseded artifacts, design classification, vertical slices, and review cadence. Record findings in
`.ai/work/<requirement-or-change-id>/REVIEW.md` or the pull request. The reviewer may advance
verified tasks to `reviewed`; findings return affected work to `in-progress` or
`blocked`.

The reviewer validates the same Security Assurance against the actual diff and may
increase its routing or required mitigations when the declared threat surface is
incomplete. The implementer's adversarial pre-review is a readiness condition, not
a substitute for independence.

The implementer remediates and reruns focused/full verification. P0/P1 fixes require
a fresh reviewer pass.

When visual review is required, code approval does not advance tasks to `reviewed`.
A fresh visual reviewer follows `.ai/roles/VISUAL_REVIEWER.md`, inspects the actual
application in a browser, and records revision-bound evidence. Only after both code
and visual approval may the last required reviewer advance verified work.

## 7. Mechanical closeout

After approval, the implementation context:

1. reconciles maintained documentation and accepted ADRs;
2. moves unresolved work to issues or `.ai/NEXT_STEPS.md`;
3. when user-facing error handling applies, reconciles the active error catalog,
   removes deprecated/orphan mappings and dead negative tests, and checks capability
   specifications for contradictory behavior;
4. runs `check-docs.py` and final `verify.sh`;
5. records outcome, verification, residual risks, and dependencies in the PR;
6. marks reviewed tasks `done`, transfers durable information, removes temporary
   work, and resets `CURRENT_PLAN.md`.

When UI quality applies, closeout also classifies every prototype element, deletes or
deliberately promotes temporary prototypes/stories, updates maintained design
sources, and removes temporary visual evidence according to
`.ai/policies/UI_QUALITY.md`.

Any material closeout change returns to review. Lasting records are accepted durable
inputs, code/tests, maintained documentation, and the pull request—not temporary task
history.

When repository-native orchestration is enabled, the trusted controller performs
the local delivery step after this closeout: final validation, exact-delta staging,
and one item-branch commit. Agent invocations never receive `.git` write access.

## Orchestrated invocations

- Work only in the staged workspace and phase supplied by the controller.
- Respect the role-specific write boundary and the additional boundaries in
  `.ai/policies/ORCHESTRATION.md`.
- Return the configured adapter's strict protocol shape: Codex uses
  `.ai/templates/CODEX_RESULT_SCHEMA.json`, while the legacy command adapter writes
  `.ai/templates/AGENT_HANDOFF.json` atomically to the request's `{handoff}` path.
- Treat proposed transitions and owner requests as advisory.
- Never edit controller state, owner decisions, queues, checkpoints, leases, or
  events.

## Status model

```text
draft → ready → in-progress → implemented → verified → reviewed → done
```

`blocked` requires a concrete blocking condition.

`CURRENT_PLAN.md` uses: `discovery`, `specification`, `planning`, `design-draft`,
`design-review`, `implementation`, `verification`, `review`, `visual-review`,
`remediation`, and `closeout`. Design-delta and visual-review verdicts remain
artifact statuses rather than a second task-status model.

## External references

Use the configured engineering-knowledge MCP only for a concrete unresolved
standards-sensitive decision when local guidance is insufficient. Record source IDs
and adopted conclusions in the specification or ADR; never store broad excerpts.
