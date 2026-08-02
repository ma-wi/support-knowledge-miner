# User-facing error handling

This is the routing and core-behavior policy for user-facing errors. Load it only
when `.ai/project.yaml` declares `user_facing_errors.enabled: true` **and** the work
adds or changes a user-triggered or user-observable action. Record
`Error handling: not-applicable: <reason>` for unaffected work without loading this
policy. It extends the canonical workflow and does not add lifecycle statuses.

Load supplements only when their configured surface applies:

| Trigger | Additional policy |
|---|---|
| API contract is enabled and the affected action has API/backend error-contract impact | `USER_FACING_ERROR_API.md` |
| Frontend handling is enabled and the affected action has browser UI error impact | `USER_FACING_ERROR_FRONTEND.md` |
| UI quality is enabled and visual error evidence is required | `UI_QUALITY_VISUAL.md` |

When disabled, the general security and safe-failure rules still apply, but the
specialized matrix, catalog, mapping, and evidence gates do not.

## Scope and invariant

Apply this policy to every new or changed user-triggered or user-observable action:
load, create, update, delete, search, import/export, upload/download,
authentication/authorization, background processing, real-time interaction, retry,
reload, cancellation, and recovery.

Every affected action has:

- a defined success path;
- classified known failure paths;
- a safe unknown-failure path;
- no false success after failure;
- input and state preservation where safe;
- an actionable recovery or support path.

## Required action contract

Before implementation, record this Error-and-Recovery Matrix:

| Action | Failure | Error code | Safe user message | Placement | Recovery | Retry | Input preservation | Tests | Logging/correlation |
|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | |

For a new capability, the accepted requirement owns the planning matrix and the
capability specification records the resulting current behavior. For an incremental
change, `CHANGE.md` owns the matrix until closeout updates the capability
specification.

Use `not-applicable: <reason>` only after verifying irrelevance. A user-facing task
cannot become `ready`, and a change cannot become `ready-for-implementation`, while a
relevant cell is unclassified.

## Known and unexpected failures

Every known failure:

- uses a stable uppercase underscore-separated code;
- has one active entry in the configured error catalog;
- states the failed action, a safe user-relevant reason, and the next action;
- defines placement, recovery, retryability, input preservation, support behavior,
  mappings, and negative tests;
- stays consistent across every applicable layer.

Prefer a domain-specific code when it enables better recovery. A generic known-error
message is invalid. Security-sensitive not-found and permission failures may
intentionally share an external message when threat analysis requires it.

Unexpected failures map to `UNEXPECTED_ERROR`. They:

- explicitly identify the failure as unexpected without exposing internals;
- provide a safe correlation or support reference when available;
- end loading/submitting state and cannot trigger success behavior;
- preserve safe input/state and offer retry, reload, return, reauthentication, or
  support as appropriate;
- are logged at the diagnostic boundary with redaction and data minimization.

Correlation identifiers contain no user, tenant, resource, secret, or sensitive data.

## Error catalog

`docs/errors/ERROR_CATALOG.md` is the default current-state index. Each active code
has exactly one entry with trigger, category, transport status when applicable,
safe title/explanation, action, retryability, placement, input preservation,
correlation behavior, security notes, layer mappings, and required tests.

Capability specifications may own detailed rows only when the central catalog links
to their exact location. Deprecated codes name their replacement, owner, and removal
criterion. Removed codes disappear from contracts, mappings, fixtures, and tests.

## Prohibited behavior

- empty catches or silently swallowed failures;
- raw exceptions, stack traces, SQL, paths, hosts, services, tokens, or secrets;
- success feedback after failure;
- ignoring an unknown code;
- generic fallback for a known code;
- parsing free-form error text for program decisions;
- treating all responses with one transport status identically;
- unplanned input loss;
- multiple competing error mappers or normalizers;
- console-only or transient-toast-only handling of a primary failure.

## Lifecycle evidence

Planning identifies actions, failures, codes, mappings, recovery, preservation,
logging, catalog impact, negative tests, legacy generic handling, and superseded
codes. Implementation traces each relevant failure end to end and proves safe unknown
behavior. Review compares the catalog, applicable layers, tests, evidence, security,
recovery, and capability specifications. Closeout removes or deprecates obsolete
codes, duplicate mappings, generic known messages, dead fixtures/tests, and
contradictory documentation.

The phase-aware checker permits incomplete discovery drafts. Readiness, Verify,
Review, and Closeout enforce the applicable declarations. Static checks supplement
negative tests, runtime inspection, threat analysis, and independent review; they do
not prove comprehension, accessibility, runtime coverage, or absence of indirect
disclosure.
