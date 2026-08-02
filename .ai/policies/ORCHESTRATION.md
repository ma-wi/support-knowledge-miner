# Repository-native orchestration

This policy defines the optional deterministic controller for the existing agent
lifecycle. `WORKFLOW.md` remains authoritative for product artifacts and task
statuses; orchestration owns queueing, invocations, checkpoints, leases, owner
gates, allowed phase transitions, and its local item branches/closeout commits.

## Trust boundaries and limits

- The host invoking `orchestrate.py decide` is the trusted owner boundary.
- Agent output, handoffs, staged files, JSON, Markdown, and process output are
  untrusted.
- Every agent invocation receives a fresh, symlink-free staged copy. With the
  default Codex adapter, the authenticated Codex CLI is a trusted host process, but
  its model-generated commands run in Codex `workspace-write` isolation against
  the stage and two empty per-invocation scratch directories, without network
  access. `/tmp` and `$TMPDIR` are excluded as implicit writable roots, so the
  sibling request, schema, and result files remain host-owned. User configuration,
  hooks, plugins, web search, dependency installation, interactive approvals, and
  persistent sessions are disabled.
- The classic Codex `workspace-write` sandbox does not deny general host reads.
  Model-generated commands may read files accessible to the invoking OS user,
  including the source repository, other repositories, and credential files, even
  though they cannot write those locations or use the network. They could copy read
  content into a promotable stage path. Enabling
  `external_repository_processing_approved` explicitly accepts this residual local
  confidentiality risk; never enable Codex orchestration on a host whose readable
  data is outside the project's accepted trust boundary.
- The stage and source digest use the same Git-tracked/non-ignored allowlist after
  removing runtime state and known local-secret paths. Git-ignored secrets, local
  overrides, environments, caches, and dependency/build output are never copied or
  hashed into agent-visible digests. Source and stage file states must match the same
  stable baseline. Aggregate byte and entry budgets are checked before copying.
- The source workspace must remain unchanged during an invocation. A changed source
  digest blocks promotion and requires human reconciliation.
- If the selected executor's required sandbox or `prlimit` is unavailable, the
  controller fails before starting the agent. Staging alone is never treated as a
  security boundary. Process count, descriptors, CPU time, wall time, aggregate
  stage size/entry count, promoted file size, output, protocol payloads, snapshots,
  and retries are bounded. The Codex host process deliberately has no `RLIMIT_AS`
  or `RLIMIT_FSIZE`: npm/Node launchers can terminate silently under those limits.
  Memory containment must therefore come from the trusted host, container, or CI
  runner; stage and promotion limits remain enforced by the controller.
- The controller has no network, deployment, credential, remote-contact, push,
  fetch, pull, merge, rebase, pull-request, or branch-deletion feature. Git is
  limited to local observation, item branches, exact staging, and closeout commits.

## Configuration and compatibility

Missing `orchestration` configuration means disabled. Disabled orchestration does not
alter the manual workflow. Every mutating command, including `intake`, and the state
gate require `enabled: true` with a non-empty argument-list executor. Agent execution
also requires attached `HEAD`, commit identity, and a clean initial worktree.
Queue-only `intake` remains branch-neutral. Item activation requires a clean
governed worktree and creates a collision-safe branch; each later item branches
from the preceding closeout commit. Tracked `assume-unchanged` or `skip-worktree`
entries are rejected before activation and closeout; the controller never rewrites
those user-owned flags. Git correctness checks use command-scoped stat, filemode,
fsmonitor, and untracked-cache overrides without changing repository or global
configuration. Legacy runtime state is not migrated.

`executor_kind: codex` is the template default. It requires
`executor_isolation: codex-sandbox`, exactly one CLI executable, an optional exact
CLI version pin, and explicit
`external_repository_processing_approved: true`. This approval records that the
project owner permits staged repository content and prompts to be processed by the
configured Codex service; it is not production authorization. `doctor` checks the
executable, version, authentication, resource limiter, configuration, and current
repository snapshot. It then runs one synthetic Codex turn through the exact
production flags and result schema. This can consume a small amount of Codex usage;
the schema is transmitted, but no project source, requirement, or queue objective is
provided to the probe.

The legacy `command` adapter remains available for local wrappers. Its arguments may
contain only `{request}`, `{handoff}`, `{workspace}`, `{role}`, and
`{invocation_id}`. It requires `executor_isolation: bwrap`; the executable must
resolve below `/usr`, `/lib`, `/lib64`, or `/bin`. It receives a minimal
environment in a Bubblewrap mount/user/network namespace.

The host writes `.ai/templates/AGENT_REQUEST.json`. A Codex invocation returns only
the semantic shape in `.ai/templates/CODEX_RESULT_SCHEMA.json`; it cannot choose
the invocation identity, source revision, source digest, staged digest, or changed
paths. The controller derives and binds those fields before validating a complete
handoff. The legacy command adapter atomically writes the complete
`.ai/templates/AGENT_HANDOFF.json` shape. A zero exit status alone is never a
successful handoff.

## Queue intake

Input is UTF-8 Markdown, at most 256 KiB and 100 items. A single non-list document is
one item. A list uses one physical line per item:

```text
- [id=REQ-001 priority=10 depends=REQ-000,REQ-000B] Summary
```

`id` is optional and must match `[A-Za-z0-9][A-Za-z0-9._-]{0,63}`. Without it, the
ID is `REQ-` plus the first twelve hexadecimal characters of the normalized summary
SHA-256. Priority defaults to `0`; higher values run first. `depends` defaults to
empty. Duplicate IDs, duplicate normalized summaries, missing dependencies,
self-dependencies, cycles, mixed list/non-list content, and unknown metadata fail
without mutation.

Only one item is active. Selection considers completed dependencies, then descending
priority, then stable intake order. `awaiting-owner` pauses the whole run; other
items remain pending.

## Phases, roles, and transitions

```text
intake       -> discovery | specification | planning       planner
discovery    -> specification | planning                   planner
specification -> design | planning                         planner
design       -> planning                                   planner
planning     -> implementation                             planner
implementation -> verification                             implementer
verification -> code-review                                controller
code-review  -> implementation | remediation | visual-review | closeout
                                                            code reviewer
visual-review -> implementation | remediation | closeout   visual reviewer
remediation  -> verification                               implementer
closeout     -> done                                       implementer
```

`intake` and `done` have no active `CURRENT_PLAN`. `design` maps to the existing
`design-draft` and `design-review` values; `code-review` maps to `review`. Other
phases use the same name. Discovery, specification, and design do not require or
create canonical tasks; the planning invocation creates them before advancing to
implementation. Task statuses remain exclusively those in `WORKFLOW.md`.

Every request contains the normalized queue objective plus the dependency- and
review-cadence-selected task IDs. `per-task`, `batch`, and `feature` cadence and the
canonical maximum batch size determine the batch. A plan may lower, but never raise,
the host-configured batch limit; later task dependencies become
eligible only after their predecessors have verified/reviewed state. Reviews may
route back to implementation for the next batch.

The handoff's proposed transition is advisory. The controller validates phase, role,
invocation, source/staged digests, and the complete changed-path boundary before
running any staged validator or reading staged semantic evidence. It then validates
canonical lifecycle state, open owner decisions, retry limits, and reviewer
independence. Verification is run by the controller through
`./.ai/tools/verify.sh`; an agent-reported pass is not authoritative.
Phase-aware work-state, incremental-change, user-facing-error, and UI validators run
against the staged proposed next phase before promotion. UI design classes 1–3
cannot route directly from code review to closeout, and classes 2–3 cannot enter
implementation without their canonical approval. Visual evidence is checked with
the existing revision/fingerprint validator.
Before an orchestrated visual-review invocation, the controller runs the configured
browser-review command as a trusted host gate against the real development/test
runtime. Only changes beneath the active UI-evidence directory are accepted. The
networkless visual-review agent independently assesses that captured interaction
evidence and never installs dependencies or starts the application inside its
namespace. Enabling orchestration together with UI quality therefore requires a
configured browser-review command; the manual browser fallback is not an
orchestrated runtime.

## Role write boundaries

- Planner: the active item's requirement, active `.ai/work/<item>/`, and
  `.ai/CURRENT_PLAN.md`. Accepted specifications and ADRs are host-owned and cannot
  be rewritten by an agent.
- Implementer: product files and the active `.ai/work/<item>/`, except
  the host-owned `.ai/CURRENT_PLAN.md`, accepted
  requirements, specifications, ADRs, `.git/`,
  controller policies/roles/tools/templates/configuration, `.ai/orchestration/`,
  `AGENTS.md`, agent rules, CI workflows, local secret/config overrides, and
  generated update patches. Changes to the protected control plane require a
  separate trusted-host workflow.
- Closeout may only remove the active work directory and reset
  `.ai/CURRENT_PLAN.md`; material changes return to verification and fresh review.
- Code and visual reviewer: their own canonical review report and status-only task
  transitions under the active
  `.ai/work/` directory only.
  Approval advances assigned `verified` tasks to `reviewed`, except that code review
  preserves `verified` while a required visual review is pending; remediation
  resets affected assigned tasks to `in-progress` or `blocked`.
- No role may write owner input, queue, lease, checkpoint, request, handoff, or event
  state in the source workspace.

Unexpected governed staged paths or symlinks fail closed. Git-ignored agent output
is excluded by the same project ignore rules used for the source and is never
promoted. Promotion prevalidates the complete delta and every target path component,
runs under the lease fencing guard, writes a recoverable `prepared` marker before
mutation, uses bounded atomic writes, restores every touched path on a caught
mutation error, and validates the source digest immediately before applying the
delta. A failed final marker write leaves the digest-bound prepared marker for
deterministic resume. A persistent, pathwise backup journal under the trusted
runtime root permits resume to restore a process-interrupted partial promotion
before retrying.
The journal binds baseline and expected source digests, every touched path's exact
before/after state, and a digest of all untouched paths. Marker states distinguish
`prepared` (no source mutation yet), `mutating`, and `committed`. Recovery restores
only a provable mixture of its own before/after path states while untouched paths
still match; any foreign change blocks without writing.
Source staging opens every path component and file descriptor-relative with
no-follow semantics, binds the copy to device, inode, size, modification time, mode,
and content digest, and rejects a source changed or replaced during copying.

## Owner gates

Owner gates are mandatory for material ambiguity, scope expansion, breaking change,
risky migration, risk acceptance, dependency exceptions, material architecture
outside delegation, required human design approval, or exceeded budgets. A decision
is bound to a stable ID, item, phase, question, allowed answers, and state digest.

The agent may request a decision but cannot apply it. The host supplies a decision
file directly to `decide`. It must be outside the repository and can be created from
`.ai/templates/OWNER_DECISION.md`; repository-local files are rejected so an agent
cannot supply trusted owner input. Stale IDs, wrong phase/digest, unknown answers, or
a claimed owner different from the configured owner fail closed. No default is
applied unless the request explicitly records one. Every `needs-owner-decision`,
`blocked`, `invalid-state`, or `retryable-failure` handoff must have an empty
repository delta; no product or lifecycle change is promoted from a non-success
result. Decisions are transferred to their canonical requirement, specification,
ADR, or design artifact before closeout.
Artifact acceptance or modification of an already accepted durable artifact requires
an exact repository path and explicit authorizing answer in the structured owner
request. The controller carries only those approved paths into the next agent
request and consumes each path authorization independently on its first matching
promotion. Owner requests remain in an immutable structured archive, so a later
handoff cannot invalidate their decisions;
unrelated decisions and free text grant no write authority.

## Persistence, resume, and failures

State is schema-versioned, size-bounded, and written atomically in
`.ai/orchestration/`. Event lines are append-only; a single truncated final line is
recoverable, while earlier corruption blocks. Timestamps, event phases/item IDs,
allowed event/result combinations, monotonic ordering, contiguous phase and status
history, and the queue/checkpoint end state are strictly cross-validated. The
`validate` command delegates to this same canonical state gate. Paths must stay
beneath their declared root after symlink resolution. Every mutating CLI path,
including `intake` and `decide`, is lease-serialized; owner decisions are also
compared with the current workspace.

One unexpired lease is allowed and is renewed during long agent and verification
runs. Resume acquires it before reconciliation. An expired lease is authorized only
after reconciliation and the takeover is recorded; direct `run`, `intake`, and
`decide` refuse an expired lease and require `resume` first. Resume validates queue,
checkpoint, handoff, lifecycle artifacts, the exact item branch, Git `HEAD`, source
digest, and existing validators before reusing evidence. A digest-bound promotion
marker is required
before a persisted handoff can advance recovery. Contradiction pauses fail-closed.

Only explicit retryable failures retry. Backoff is persisted rather than slept.
Retry signatures contain normalized error categories, never raw output. Identical
failure and per-phase limits produce `blocked`. P0/P1 findings are remediation, not
technical retries, and require a fresh reviewer invocation. A remediation handoff
must contain findings whose exact identifiers or text occur in the canonical,
digest-bound review report.

## Closeout

After review, closeout may add only validated temporary-work removal and
`CURRENT_PLAN.md` reset; material change returns to verification and review. The
controller checkpoints the closed state, runs final documentation/full verification,
rejects runtime/secret/foreign paths and index entries, and stages the exact delta.

Parent, tree, digest, deterministic subject and branch intent bind one noninteractive
commit with hooks, signing, editors and prompting disabled. Resume adopts only that
commit. After the queue completes, active runtime is removed under the lease fence;
an ignored receipt retains branches/commits for `status`. Prompts, output, secrets,
personal data, stages, and runtime state are never committed or copied.
