# Change impact: <title>

- Change ID: <CHG-###>
- Status: draft | complete | accepted
- Change request: `.ai/work/<change-id>/CHANGE.md`
- Last updated:

## Search scope and current-state findings

Record repositories, directories, symbols, contracts, databases, generated artifacts,
and documentation searched. Summarize only relevant findings.

## Impact matrix

Use exactly one action per located responsibility: `keep`, `modify`, `migrate`,
`deprecate`, `remove`, `replace`, or `not-applicable`.

| Layer or concern | Located artifact / current owner | Action | Required end state | Owning task | Verification evidence |
|---|---|---|---|---|---|
| UI and interaction state | | | | | |
| Frontend validation and feature model | | | | | |
| API client / generated artifacts | | | | | |
| Public API or message contract | | | | | |
| Backend schema and application service | | | | | |
| Domain model and business rules | | | | | |
| Persistence and migration | | | | | |
| Integrations, jobs, events, caches, search | | | | | |
| Telemetry and operations | | | | | |
| Tests and fixtures | | | | | |
| Documentation and specifications | | | | | |

Remove genuinely irrelevant example rows only after recording how irrelevance was
verified. Add project-specific rows where necessary.

## New or parallel artifacts

| Proposed artifact | Existing responsibility searched | Why extension/replacement is insufficient | Compatibility need | Removal criterion |
|---|---|---|---|---|
| | | | | |

Use `none` when no new or parallel artifact is proposed.

## Superseded artifacts

| Artifact | Disposition: remove/deprecate/replace/retain | Reason if retained | Owning task | Removal criterion or evidence |
|---|---|---|---|---|
| | | | | |

Use `none` only after searching for obsolete code, contracts, tests, fixtures,
configuration, dependencies, and documentation.

## Concept-trace completion

- Repository-wide search terms and symbols:
- Generated sources traced to their authoritative input: yes | no | not-applicable
- No relevant references remain unclassified: yes | no
- Uncertainty or intentionally excluded areas:

## Acceptance

- Impact analysis complete: yes | no
- Accepted by:
- Date:
