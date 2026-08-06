# ADR-0007: Indizierungen, Cluster-Sets and provider-purpose split

- Status: accepted
- Date: 2026-08-04
- Last amended: 2026-08-05 by CHG-005 provider settings centralization
- Owners: anfordernder Product Owner
- Related requirement: `docs/requirements/chg-004-analyst-clustering-redesign.md`
- Supersedes: ADR-0003
- External reference identifiers: none

## Context

The accepted analyst workflow needs model choices at different decision points.
Analysis profiles mixed embedding configuration, clustering parameters and
LLM/prompt behavior in one project-scoped object. That prevented a clear workflow
for repeated indexing, multiple cluster-set variants, hierarchical refinement and
LLM-generated cluster summaries.

The tool is local/private and does not need compatibility for the removed profile
model. The accepted migration may drop old local derived data such as analysis
profiles, old runs, embeddings, clusters and candidates, while retaining projects,
users, provider configurations, imports and dataset versions.

## Decision

Remove analysis profiles as an active domain, API and UI concept.

Use `IndexingRun` / „Indizierung“ for embedding generation. An indexing run selects
one embedding provider/model and creates both `message` and `answer` embeddings for
every valid support pair in the selected dataset version.

Use `ClusterSet` for clustering results. A cluster set selects a completed indexing
run, vector basis, algorithm, algorithm parameters, source set and optional
LLM-provider/model for summaries. Every structural recalculation, refinement,
source change or outlier exclusion creates a new cluster set instead of overwriting
the parent.

Store cluster-set lineage through parent links, derivation type and immutable source
snapshots. The UI presents saved sets as an expandable analysis tree.

Keep provider configuration global and purpose-aware:

- Provider instances have a stable technical ID, editable display name and base
  type.
- Active base types are OpenAI and Ollama.
- Each provider instance stores available/discovered models plus separate embedding
  and LLM allow-lists. Purpose availability is derived from non-empty allow-lists.
- vLLM is removed from active UI/API/runtime support. Historical provenance may
  remain readable, but vLLM is not selectable or callable for new work.

OpenAI remains explicit cloud use. Original support text may be sent to OpenAI only
after confirmation for the concrete indexing or LLM-summary action. Local provider
endpoints remain local-host allow-listed and secrets remain write-only.

Remove the separate candidate workflow from the active analysis path. The cluster
set is the final analysis artifact. Explorer export belongs to the Explorer and
exports the current filtered cluster table state as CSV or JSON.

## Alternatives considered

- Keep analysis profiles and add more fields: rejected because profiles remain the
  wrong decision point for embedding, clustering and LLM choices.
- Rename runs only in the UI: rejected because persistence and API would still
  encode profile-scoped behavior.
- Keep candidates as the final artifact: rejected because the accepted workflow
  analyzes and exports cluster-set results directly.
- Mutate a cluster set in place during refinement or outlier exclusion: rejected
  because analysts need traceable hierarchy and reproducible prior states.
- Merge embedding and LLM providers into one model list: rejected because embedding
  and chat/generation models have different contracts, validation, prompts and
  cloud-confirmation behavior.

## Consequences

### Positive

- The analyst can run multiple embeddings and cluster sets without profile
  indirection.
- Cluster parameters and LLM summary parameters are stored with the result they
  produced.
- Hierarchical exploration remains traceable through parent links and source
  snapshots.
- Provider configuration stays reusable while model choices stay explicit at the
  action that sends data.
- The UI can focus on Import → Indizieren → Cluster-Sets → Explorer.

### Negative

- This is a breaking local migration for old profile/run/cluster/candidate derived
  data.
- API, schema, services, tests and UI must be replaced across several layers.
- LLM summary generation introduces a second provider purpose and additional
  failure modes.

## Risks and mitigations

- Risk: accidental cloud submission of sensitive support text.
- Mitigation: OpenAI use is explicit per indexing or LLM-summary action and requires
  immediate confirmation before text transfer.

- Risk: loss of useful derived local data during migration.
- Mitigation: accepted scope permits dropping old derived data; migration keeps
  projects, users, provider settings, imports and dataset versions.

- Risk: lineage becomes misleading after parent edits or deletion.
- Mitigation: child cluster sets store immutable source snapshots; deleted parents
  remain visible as non-loadable history nodes when needed.

- Risk: LLM output is malformed or unsafe to trust.
- Mitigation: treat provider output as untrusted input, validate against a strict
  schema, bound sizes/timeouts and avoid exposing raw provider bodies.

- Risk: clustering or LLM work exhausts local resources.
- Mitigation: keep existing bounded provider batches, chunking, clustering budget
  checks, algorithm limits, job queues, cancellation and safe failure behavior.

## Validation

- Migration tests prove old profile/run/candidate-derived state is removed or
  migrated according to accepted scope while retained data remains accessible.
- Provider tests prove provider instances, available models, embedding/LLM
  allow-lists and active vLLM rejection.
- Indexing tests prove every valid support pair gets both `message` and `answer`
  embeddings with safe progress/error behavior.
- Cluster-set tests prove multiple saved sets, parent/child lineage, source
  snapshots, vector-basis selection and no in-place structural overwrite.
- LLM tests prove summary schema validation, random sample count/default behavior,
  all-examples mode, OpenAI confirmation and safe failure handling.
- Explorer/API/UI tests prove table view, source dialog, outlier box, refinement and
  filtered CSV/JSON export.
