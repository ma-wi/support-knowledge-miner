## Error and recovery behavior

For each user-triggered or user-observable action, record the resulting current
Error-and-Recovery Matrix:

| Action | Failure | Error code | Safe user message | Placement | Recovery | Retry | Input preservation | Negative tests | Logging/correlation |
|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | |

### Invariants

- User input is retained after unsuccessful submission where safe.
- A failed operation is never reported as successful.
- Known error codes never fall back to a generic message.
- Unexpected errors include a support reference when available.
- Raw technical exception details are never displayed.
