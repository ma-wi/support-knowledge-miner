# Threat model: Manuelle Cluster-Kuration und direkte Explorer-Bearbeitung

- Requirement ID: chg-016-manual-cluster-curation
- Status: draft
- Decision owner: mawi
- Last updated: 2026-08-19

## Scope

- System or feature: Explorer manual cluster creation, single-cluster LLM refresh,
  reference similarity preview, inline editing and source-to-outlier moves.
- In scope: authenticated project API, PostgreSQL persistence, local embeddings,
  optional OpenAI/Ollama LLM calls, bounded UI inputs and audit events.
- Out of scope: production, live support systems, customer communication and new
  external integrations.
- Assumptions: only local/development/test resources with no production data.

## Assets and data classes

| Asset or data | Classification | Owner | Retention | Protection required |
|---|---|---|---|---|
| Imported customer messages and support answers | confidential | project owner | existing project lifecycle | project scoping, bounded source access, no raw logs |
| User-entered examples and FAQ fields | confidential | project owner | manual cluster lifecycle | bounded storage, safe errors, no raw diagnostics |
| Embeddings and similarity scores | internal/confidential | project owner | existing indexing/cluster lifecycle | project scoping, dimension/resource limits |
| LLM provider credentials/configuration | secret/internal | project owner | existing provider policy | write-only secret handling, no disclosure |
| Manual membership/audit metadata | internal | project owner | cluster-set lifecycle | transaction, authorization, no complete ID lists in logs |

## Trust boundaries

| Boundary | Untrusted side | Trusted side | Controls |
|---|---|---|---|
| Browser to API | client payloads, IDs, text, scope, thresholds | FastAPI/service | auth, project checks, Pydantic bounds, server-side authorization |
| API to PostgreSQL | validated but concurrent request state | database | parameterized SQL, transactions, unique membership constraint, conflict/version check |
| Backend to LLM provider | original/example support text and provider response | configured provider call | explicit provider/model, OpenAI confirmation, bounded prompt/output, schema validation, redacted diagnostics |
| Backend similarity computation | query text and candidate vectors | local process/memory | bounded examples/candidates/dimensions/time, no unbounded pairwise matrix |
| API response to browser | source text and untrusted generated fields | React rendering | safe structured response, escaping, bounded pages, central error mapping |

## Threats and mitigations

| ID | Threat | Impact | Mitigation | Verification |
|---|---|---|---|---|
| T-1 | Cross-project cluster/pair ID submitted by client | data disclosure or mutation | project-scoped joins and authorization at every mutation | API negative tests |
| T-2 | LLM response injects invalid/unsafe fields or assignments | corrupt metadata or wrong membership | strict structured parsing, field bounds, known IDs only, transactional commit | malformed/schema/unknown-ID tests |
| T-3 | Support text or prompt appears in logs/errors | confidential data disclosure | aggregate diagnostics, redaction, safe Problem Details | logging/error assertions |
| T-4 | OpenAI receives text without explicit consent | privacy violation | existing cloud confirmation and provider/model validation | API/UI confirmation-negative tests |
| T-5 | Large candidate scope/examples cause memory/time exhaustion | local availability loss | hard limits, bounded batches, timeout/cancellation, no all-pairs matrix | resource-bound tests |
| T-6 | Concurrent autosaves overwrite newer edits | silent data loss | field-scoped optimistic version/conflict handling and rollback | concurrent update tests |
| T-7 | Retry repeats source move or creates duplicate cluster/membership | inconsistent curation | idempotency/unique constraints and transactional re-read | replay/retry tests |
| T-8 | Failed optimistic UI write reports success | analyst believes wrong state is saved | central error handling, rollback, no success after rejection | frontend failure tests |
| T-9 | Manual source move bypasses generated-set immutability | history corruption | only `manual_edit` child mutable; auto sets reject mutation | service negative tests |
| T-10 | Raw source rendered in unsafe context | browser injection | React escaped text rendering, no raw HTML path | rendering/security tests |
| T-11 | Single-cluster refresh accidentally overwrites neighboring summaries or memberships | analyst data loss | target-cluster transaction, field-scoped update and invariant tests | service/API regression tests |
| T-12 | Reference selection crosses the chosen scope or leaks excluded/project data | disclosure or wrong analyst decision | server-side reference/scope validation and bounded result contract | scope/isolation negative tests |
| T-13 | Many references multiply similarity work beyond local limits | availability loss | cap references/results/candidate rows and use bounded vector work | resource-bound tests |

## Residual risk

| Risk | Severity | Owner | Expiry or follow-up |
|---|---|---|---|
| Semantic similarity threshold may produce false positives and requires analyst confirmation | P2 | mawi | Keep preview/explicit selection; review after first use |
| Manual-edit child can grow through repeated local edits | P2 | mawi | Bound membership operations and document lifecycle |

## Acceptance

- Accepted by:
- Date:
- Conditions: D001–D011 and specialist security review must be accepted before implementation readiness.
