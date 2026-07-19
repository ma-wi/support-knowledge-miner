# Canonical agent workflow

This file owns lifecycle and status transitions; role files add only role-specific
responsibilities. Use one active requirement per branch/worktree.

```text
planner → implementer → independent reviewer
                    ↖ remediation ↙
                 mechanical closeout
```

Testing, security, dependencies, and documentation are conditional review lenses.
Use a specialist context only for significant risk or an explicit requirement.
Trivial work uses the reduced path in `AGENTS.md`: no temporary work directory, only
the relevant checks, and no planner/implementer/reviewer split unless risk demands it.

## 1. Intake and classification

The planner reads the requirement, configuration, context, applicable ADRs, and
relevant code/tests. Record the `trivial`, `normal`, or `significant` class defined in
`AGENTS.md`; material uncertainty raises the class.

## 2. Discovery and durable specification

For significant or materially unclear work, create
`.ai/work/<requirement-id>/DISCOVERY.md` from
`.ai/templates/FEATURE_DISCOVERY.md`. Resolve only decisions that can change outcome,
scope, behavior, risk, architecture, or acceptance criteria, then obtain explicit
shared-understanding confirmation.

Store significant specifications at `docs/specifications/<requirement-id>.md`. They
own observable behavior, scope, accepted decisions, criteria, and stable test seams.
Agents propose requirements, specifications, and ADRs; a named authorized decision
owner records acceptance. Dependent implementation waits for accepted ADRs and:

```text
Status: ready-for-implementation
Ready for implementation: yes
```

## 3. Temporary planning

Normal/significant work uses:

```text
.ai/work/<requirement-id>/
├── DISCOVERY.md           # only when needed
├── PLAN.md
└── tasks/                 # only independently implementable units
```

The plan links to durable inputs and records approach, sequence, affected areas,
risks, verification, migration/recovery, and documentation. Update
`.ai/CURRENT_PLAN.md`. Planner task statuses are `draft` or `ready`.

## 4. Implementation

The implementer takes a `ready` task, marks it `in-progress`, and implements the
smallest coherent behavior slice with tests. Record material deviations before
continuing. After code/tests are complete mark `implemented`; after focused checks
pass mark `verified`.

## 5. Full verification

Run `./.ai/tools/verify.sh`. It runs locked setup for configured projects, then every
configured mandatory gate. Every mandatory gate must execute and pass; a mandatory
skip fails. Record exact commands/results and environment limitations.

## 6. Independent review and remediation

A fresh reviewer context compares requirement, specification, ADRs, plan, full diff,
tests, verification, and affected documentation. Record findings in
`.ai/work/<requirement-id>/REVIEW.md` or the pull request. The reviewer may advance
verified tasks to `reviewed`; findings return affected work to `in-progress` or
`blocked`.

The implementer remediates and reruns focused/full verification. P0/P1 fixes require
a fresh reviewer pass.

## 7. Mechanical closeout

After approval, the implementation context:

1. reconciles maintained documentation and accepted ADRs;
2. moves unresolved work to issues or `.ai/NEXT_STEPS.md`;
3. runs `check-docs.py` and final `verify.sh`;
4. records outcome, verification, residual risks, and dependencies in the PR;
5. marks reviewed tasks `done`, transfers durable information, removes temporary
   work, and resets `CURRENT_PLAN.md`.

Any material closeout change returns to review. Lasting records are accepted durable
inputs, code/tests, maintained documentation, and the pull request—not temporary task
history.

## Status model

```text
draft → ready → in-progress → implemented → verified → reviewed → done
```

`blocked` requires a concrete blocking condition.

## External references

Use the configured engineering-knowledge MCP only for a concrete unresolved
standards-sensitive decision when local guidance is insufficient. Record source IDs
and adopted conclusions in the specification or ADR; never store broad excerpts.
