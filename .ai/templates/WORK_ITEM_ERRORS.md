## Error and recovery implementation

Append this annex only when user-facing error handling applies.

### User actions covered

- Load:
- Create:
- Update:
- Delete:
- Search:
- Import:
- Export:
- Upload:
- Download:
- Background action:
- Other:

### Expected failures

| Error code | Trigger | Backend mapping | UI placement | User message | Recovery |
|---|---|---|---|---|---|
| | | | | | |

### Unknown failure behavior

- User-facing fallback:
- Correlation ID:
- Retry behavior:
- Input preservation:
- Support behavior:

### Required negative tests

- [ ] Validation failure
- [ ] Authentication failure
- [ ] Authorization failure
- [ ] Not found
- [ ] Conflict or concurrent change
- [ ] Business-rule failure
- [ ] Dependency unavailable
- [ ] Network failure
- [ ] Timeout
- [ ] Cancellation
- [ ] Unexpected server error
- [ ] Unknown error code
- [ ] Failed optimistic update
- [ ] No false success feedback

Mark irrelevant items `not-applicable: <reason>`.

### Error acceptance criteria

- [ ] Every changed action handles failure.
- [ ] Known failures use specific catalogued codes and actionable messages.
- [ ] Unknown failures use the safe fallback and correlation behavior.
- [ ] Failed writes preserve safe input and cannot display success.
- [ ] Applicable backend, contract, client, and frontend mappings agree.
- [ ] Raw technical details are not displayed.
- [ ] Required runtime or visual evidence exists.
