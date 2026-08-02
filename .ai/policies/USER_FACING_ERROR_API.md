# User-facing error API and backend contract

Load this supplement when user-facing error handling and its API contract are enabled
and the affected action has API/backend error-contract impact. Also follow the core
`USER_FACING_ERROR_HANDLING.md`.

## Problem Details contract

Use RFC 9457 Problem Details where the stack supports it. The configured baseline
fields are:

| Field | Requirement |
|---|---|
| `type` | Stable problem type URI or documented category. |
| `title` | Short safe summary. |
| `status` | Transport status represented by this occurrence. |
| `detail` | Safe explanation; clients never parse it. |
| `code` | Stable machine-readable decision key. |
| `correlationId` | Safe diagnostic/support reference. |
| `retryable` | Whether another attempt may help. |
| `suggestedAction` | Stable next-action code. |
| `fieldErrors` | Typed field errors; empty when none. |

Clients branch on `code`, never on `detail` or status alone, safely ignore unknown
fields, and handle unknown codes. `fieldErrors.field` uses a stable client field
identity.

Baseline suggested actions are `correct-input`, `retry`, `reload`,
`reauthenticate`, `return`, `contact-support`, `resolve-conflict`, and `cancel`.
Projects may define additional stable values in their contract.

## Backend ownership

Use one central path:

```text
domain / validation / identity / infrastructure error or unexpected exception
    -> central error mapper
    -> Problem Details response
```

The backend:

- models domain and validation failures explicitly;
- handles authentication and authorization at protected boundaries;
- maps infrastructure and unexpected failures without exposing internals;
- attaches a safe correlation ID where possible;
- records diagnostic detail server-side subject to redaction and minimization;
- maps the same domain error consistently across endpoints;
- keeps status, code, type, catalog, schema, and generated client aligned.

No raw exception object or message crosses the boundary.

## Compatibility

Code rename or removal requires an explicit compatibility decision plus coordinated
contract, catalog, generated-client, consumer, test, and documentation changes.
Authentication, permission, and not-found responses disclose no attacker-useful
information.

## Required verification

For every relevant code:

- backend tests trigger the condition and assert status, code, safe title/detail,
  retryability, action, field errors, correlation behavior, and absence of internals;
- contract tests assert schema, typed fields, code/status consistency, generated
  clients, removed-code absence, and unknown-code behavior;
- logging tests verify redaction and correlation where observable;
- negative tests cover validation, identity, permission, not-found, conflict,
  business rules, dependencies, timeouts, cancellation, and unexpected failures when
  applicable.

## Backend-only projects

Set `user_facing_errors.frontend.enabled: false`. Keep this supplement enabled for an
exposed API. Record UI-specific matrix rows as `not-applicable` with the verified
reason; do not load the frontend or visual supplements.
