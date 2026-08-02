# User-facing error frontend behavior

Load this supplement when user-facing error handling and frontend handling are
enabled and the affected action has browser UI error impact. Also follow
`USER_FACING_ERROR_HANDLING.md` and, when an API is involved,
`USER_FACING_ERROR_API.md`.

## Central ownership

Use one central normalization and mapping path:

```text
API response / network failure
    -> normalizeApiError()
    -> application error
    -> stable-code mapping
    -> presentation component
```

All API/network failures pass through it. Components do not parse backend text or
branch only on status. Each known code has one specific mapping; unknown codes use a
safe fallback. Competing component-local normalizers are forbidden.

## Interaction invariants

- Field errors attach semantically to the correct fields.
- Failed writes preserve values where safe.
- Failed optimistic updates roll back.
- Loading/submitting states end and controls recover after failure.
- Success state or notification cannot run after failure.
- Focus, keyboard operation, labels, and alert semantics are implemented.
- Errors are not handled only through console logging or a transient toast.
- React Error Boundaries cover unexpected render failure only, not API, validation,
  or domain errors.

## Presentation

- **Inline field:** formats, ranges, required values, or field-specific rules.
- **Form banner:** failed write, conflict, permission, network, or server failure.
- **Component state:** one bounded region failed while the rest remains usable.
- **Page state:** primary page content is unavailable.
- **Toast:** supplementary or non-blocking background feedback only.
- **Fatal fallback:** unexpected application/render failure with safe recovery.

Every known message names the failed action, gives the safe user-relevant reason, and
states the next action. The unknown fallback names the affected action/view, says the
failure was unexpected, offers recovery, preserves safe state, and shows a safe
reference when available.

## Required verification

Frontend tests cover applicable code mapping, placement, field association, input
preservation, retry/reload, rollback, loading termination, focus, unknown fallback,
no false success, and absence of raw technical detail.

Browser/E2E tests exercise relevant validation, permission, not-found, conflict,
business-rule, dependency, network, timeout, unexpected, and unknown-code paths.
They assert visible text, placement, recovery controls, focus, retained input, no
success feedback, responsive layout, safe reference, and no internals.

When UI-quality evidence is required, also load `UI_QUALITY_VISUAL.md`; screenshots
and code inspection do not replace interaction tests.
