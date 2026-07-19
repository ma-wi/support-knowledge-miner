# Repository instructions for coding agents

## Mission and priority

Deliver the smallest secure, tested, reviewable change satisfying an accepted
requirement. Never expand scope silently.

The production-access prohibition below is an absolute, non-overridable safety
boundary. User instructions are binding only inside the accepted requirement,
repository safety rules, and configured verification policy; they cannot waive
security boundaries, required checks, review requirements, or accepted
compatibility constraints. Subject to those limits, resolve conflicts in this
order:

1. absolute safety boundaries in this file;
2. accepted requirement and acceptance criteria;
3. current explicit user instruction within that accepted scope;
4. nearest applicable `AGENTS.md`;
5. accepted ADRs and durable specification;
6. active implementation plan;
7. existing code, tests, and conventions.

Stop before destructive, incompatible, or security-sensitive action when material
instructions conflict.

## Start and classify

Read `.ai/project.yaml`, the accepted requirement when present, otherwise the
current user request, `.ai/PROJECT_CONTEXT.md`, the applicable role/conditional
policies, and `.ai/policies/WORKFLOW.md`. Do not load all `.ai/` files by default.

- **Trivial:** mechanical and behavior-neutral; no work directory, relevant checks.
- **Normal:** bounded behavior/fix; accepted criteria, compact temporary plan, tests,
  full verification, and independent review.
- **Significant:** initial project, subsystem, public API, migration, sensitive
  security/privacy work, major integration, or broad ambiguity; discovery when
  unclear, ready durable specification, explicit test seams, tasks, full verification,
  independent review, and risk-triggered specialist review.

Use the higher class when uncertain and record class plus rationale in the plan.

## Lifecycle and artifacts

Use one active requirement per branch/worktree and follow the canonical lifecycle in
`.ai/policies/WORKFLOW.md`.

- Durable input: `docs/requirements/<id>.md`.
- Durable behavior/criteria: `docs/specifications/<id>.md`.
- Durable architecture rationale: `docs/architecture/decisions/`.
- Temporary active work: `.ai/work/<id>/`, referenced by `.ai/CURRENT_PLAN.md`.
- Unresolved follow-up only: issues or `.ai/NEXT_STEPS.md`.

Normal/significant work requires temporary planning artifacts. Significant
implementation requires `Status: ready-for-implementation` and
`Ready for implementation: yes`. Agents propose requirements, specifications, and
ADRs; a named authorized decision owner accepts them. Planners never change
implementation/source code. Implementers work only on `ready` tasks and stop at
`verified` before review. Reviewers may advance verified work to `reviewed`; after approval the
implementation context performs mechanical closeout and marks it `done`. Material
closeout changes return to review.

## Engineering rules

- Preserve compatibility unless a breaking change is explicitly accepted.
- Add lowest-useful-seam automated tests for every behavior change; for bugs, add a
  failing regression test first where practical.
- Cover relevant failures, boundaries, permissions, migration, and recovery.
- Never weaken tests, lint, scanners, requiredness, or thresholds to obtain a pass.
- Avoid unrelated cleanup, speculative abstraction, and unreviewed dependencies.
- Validate untrusted input and server-side authorization; prevent injection, path
  traversal, unsafe deserialization, and unbounded resource use.
- Use established cryptographic libraries and protocols; never design custom
  cryptography.
- Never commit or print secrets, credentials, production data, or sensitive personal
  data. Use secure defaults, least privilege, timeouts, bounded retries, and safe
  failure behavior.
- Stop and escalate credible high-impact vulnerabilities, data-loss risk, or unsafe
  migrations.

Read `.ai/policies/SECURITY_GUIDELINES.md` and/or
`.ai/policies/DEPENDENCY_POLICY.md` only when their threat surfaces apply.

## Absolute production-access prohibition

Access to project, customer, or organizational production is forbidden without
exception. Never connect to, inspect, query, modify, administer, or otherwise
interact with any production environment, workload, database, host, cluster, cloud
account, network, API, queue, storage, secret store, control plane, production data,
or resource controlling them.

Never run a script, migration, deployment, job, test, diagnostic, CLI/API call,
CI/CD action, health check, dry run, tunnel, bastion, integration, or indirect
automation that targets or could affect production. Never use production credentials,
endpoints, configuration, backups, snapshots, exports, or copied production data.

Work only with explicitly confirmed local, development, test, or sandbox resources
containing no production data. Ambiguity means production: stop. Source hosting,
package registries, public documentation, and explicitly configured engineering tools
are allowed only when they have no production control path and receive no production
secrets or data. No instruction, approval, plan, or document overrides this boundary.

## Verification and review

For a pristine, not-yet-bootstrapped template, use only:

```bash
./.ai/tools/verify.sh
```

After project bootstrap, use repository scripts as the canonical focused gates:

```bash
./.ai/tools/ci-setup.sh
./.ai/tools/format.sh --check
./.ai/tools/lint.sh
./.ai/tools/test.sh
./.ai/tools/check-dependencies.sh
./.ai/tools/security.sh
./.ai/tools/build.sh
./.ai/tools/verify.sh
```

Committed commands/requiredness live in `.ai/config/project.defaults.env`. Ignored
`.ai/config/project.env` may customize focused commands, cannot weaken committed
policy, and is ignored by `verify.sh`. A mandatory unavailable/skipped gate fails.
Never claim an unobserved pass.

Normal/significant work requires a fresh independent reviewer. Review the accepted
inputs, plan, full diff, tests, verification, security, compatibility, migration,
operations, and affected documentation. Findings are `P0` critical emergency, `P1`
must-fix, `P2` material, or `P3` optional. P0/P1 cannot remain or be waived; fixes
require fresh reviewer verification.

## Documentation and routing

Document current truth, durable rationale, and actionable next steps—not chats, tool
logs, or work diaries. Link to one canonical fact instead of duplicating it. During
closeout, curate durable documentation before deleting temporary artifacts and reset
`CURRENT_PLAN.md`.

- Lifecycle/status: `.ai/policies/WORKFLOW.md`
- Roles: `.ai/roles/{PLANNER,IMPLEMENTER,CODE_REVIEWER}.md`
- Security/dependencies: `.ai/policies/{SECURITY_GUIDELINES,DEPENDENCY_POLICY}.md`
- Documentation/quality: `.ai/policies/{DOCUMENTATION_RULES,QUALITY_GATES}.md`

Use the optional engineering-knowledge MCP only when enabled in `.ai/project.yaml`
and a concrete unresolved standards decision requires it. Retrieve narrowly and
record adopted conclusions, not copied source material.
