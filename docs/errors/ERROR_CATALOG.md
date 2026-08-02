# Error catalog

This catalog indexes the current active user-facing error contract. Add product and
capability-specific codes as behavior is implemented. The canonical rules and field
semantics are in `.ai/policies/USER_FACING_ERROR_HANDLING.md`.

## Catalog contract

Every active known code has exactly one entry with:

- Status: `active` or `deprecated`
- Category
- Trigger
- HTTP status or `not-applicable`
- Problem type
- User-facing title
- User-facing explanation
- Suggested action
- Suggested action code
- Retryable
- UI placement or `not-applicable`
- Input preservation
- Correlation reference
- Security considerations
- Backend source
- API contract
- Frontend mapping or `not-applicable`
- Required tests
- Replacement and removal criterion when deprecated

Codes use stable uppercase letters, digits, and underscores. General categories do
not hide a specific domain reason when that reason enables a better recovery action.

## Baseline categories

| Code | Default category | Typical status | Default recovery |
|---|---|---:|---|
| `VALIDATION_FAILED` | validation | 422 | correct-input |
| `AUTHENTICATION_REQUIRED` | authentication | 401 | reauthenticate |
| `PERMISSION_DENIED` | authorization | 403 | return or contact-support |
| `RESOURCE_NOT_FOUND` | not-found | 404 | return |
| `RESOURCE_CONFLICT` | conflict | 409 | correct-input or return |
| `CONCURRENT_MODIFICATION` | concurrent-modification | 409 | reload |
| `BUSINESS_RULE_VIOLATION` | business-rule | 422 | project-defined |
| `RATE_LIMITED` | rate-limit | 429 | retry |
| `DEPENDENCY_UNAVAILABLE` | dependency | 503 | retry |
| `REQUEST_TIMEOUT` | timeout | 504 | retry |
| `NETWORK_UNAVAILABLE` | network | not-applicable | retry |
| `OPERATION_CANCELLED` | cancellation | not-applicable | return |
| `UNEXPECTED_ERROR` | unexpected | 500 | retry or contact-support |

These rows define available categories, not automatically active product errors.
Active codes are declared below or indexed to a capability catalog.

## Active entries

None. Baseline categories are available vocabulary, not active product behavior.

## Entry template

### `CUSTOMER_VERSION_CONFLICT`

- Status: active
- Category: concurrent modification
- Trigger: The submitted version differs from the current persisted version.
- HTTP status: 409
- Problem type: `https://example.test/problems/customer-version-conflict`
- User-facing title: Der Kunde wurde nicht gespeichert.
- User-facing explanation: Der Datensatz wurde zwischenzeitlich geändert.
- Suggested action: Laden Sie den aktuellen Stand und wiederholen Sie Ihre Änderung.
- Suggested action code: reload
- Retryable: yes-after-reload
- UI placement: form-banner
- Input preservation: Preserve unsaved input until the user confirms reload.
- Correlation reference: optional
- Security considerations: Do not disclose another editor's identity unless allowed.
- Backend source: `CustomerVersionConflict`
- API contract: OpenAPI `ProblemDetails` response for customer update
- Frontend mapping: central `ApplicationError` mapping
- Required tests:
  - backend mapping test
  - API contract test
  - frontend mapping test
  - interaction test

The entry above is a template example and is not an active code until a project
removes this sentence and declares it in an active capability.

## Capability catalogs

None.

## Deprecated entries

None.
