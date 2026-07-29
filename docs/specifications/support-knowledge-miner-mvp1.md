# Feature specification: Support Knowledge Miner MVP 1

- Requirement ID: support-knowledge-miner-mvp1
- Status: ready-for-implementation
- Ready for implementation: yes
- Requirement source: `docs/requirements/support-knowledge-miner-mvp1.md`
- Accepted incremental requirements:
  `docs/requirements/chg-001-browser-session-live-run-status.md`,
  `docs/requirements/chg-002-analysis-clustering-feedback.md`
- Decision owner: User
- Last reviewed: 2026-07-28

## Purpose

Support Knowledge Miner MVP 1 provides a local-first project workspace for importing, analyzing, curating, persisting, reopening, and exporting historical support knowledge extracted from already-paired customer-message/support-answer records. It must preserve source traceability, support global model-provider configuration with per-analysis-profile model selection, provide simple equal-permission user management, and keep project state durable in local persistent storage.

## Existing context and terminology

- Applicable ADRs: ADR-0001, ADR-0002, ADR-0003, ADR-0004, ADR-0005, ADR-0006.
- Existing domain terms and definitions:
- `Project`: top-level independent workspace containing all imported data, profiles, runs, curation, candidates, exports, and artifact references.
- `DatasetVersion`: immutable version of imported valid source records within one project.
- `MessagePair`: one already-paired customer message and support answer imported from CSV or JSON.
- `AnalysisProfile`: project-scoped configuration for provider/model, algorithms, prompts, thresholds, and runtime parameters.
- `ProviderConfiguration`: global connection and credential configuration for providers such as OpenAI, Ollama, and vLLM.
- `User`: authenticated local application user with first name, last name, email, and password hash. The email address is the login identifier.
- `AnalysisRun`: one execution of one analysis profile over one dataset version.
- `Embedding`: persisted vector representation associated with a source text, text variant, segment, cluster, or candidate as applicable.
- `Cluster`: automatically generated grouping of semantically/structurally similar records or derived items.
- `Candidate`: curated support knowledge item such as static FAQ, parameterized FAQ, dynamic case, text block, single case, or not usable.
- `ManualOverride`: user-provided change that supersedes an automatic value while preserving the automatic source value.
- `ImportLog`: persisted report of import outcome, including skipped rows/objects and reasons.
- Terminology decision: PostgreSQL with pgvector supersedes the draft Lastenheft reference to MongoDB.

## Scope

### In scope

- Project lifecycle: create, open/list, rename, delete.
- Project isolation for all persisted data and artifacts.
- CSV import with source fields `ticket_id`, `message_group_id`, `message`, `answer`.
- JSON import as a list of objects with equivalent fields.
- Import validation, skipped-record behavior, and persisted import logs.
- PostgreSQL with pgvector as primary local database with persistent Docker volume.
- Persistent storage of source text, metadata, datasets, analysis profiles, analysis runs, embeddings/vector data where practical, clusters, curation, candidates, audit/import/export metadata.
- Project-scoped persistent file/volume storage for bulky non-query artifacts such as model caches and generated export files.
- Analysis profiles scoped within projects.
- Global provider configuration for OpenAI API key plus Ollama/vLLM connection and model discovery.
- Analysis-profile model selection from globally configured provider models.
- Simple authentication and equal-permission user management.
- Docker Compose local runtime with PostgreSQL/pgvector and local Ollama/vLLM paths.
- GPU-default local runtime with CPU fallback.
- Background analysis job state and reproducibility metadata.
- Scalable clustering foundation that avoids full pairwise all-record distance matrices.
- Real `message` embeddings from the explicitly selected OpenAI, Ollama, or vLLM
  model and executable HDBSCAN/Agglomerative clustering.
- Manual curation separation between automatic, manual, and effective values.
- Candidate/source traceability.
- Candidate and source-assignment CSV exports using accepted field baselines.
- Synthetic fixtures for acceptance tests.

### Out of scope / non-goals

- Production access, production data, or any production-control path.
- Server deployment.
- Live support/ticket/shop/ERP/shipping/repair integrations.
- Operational FAQ answering for new messages.
- Customer communication.
- Differentiated role and approval workflow.
- Automatic pair inference from ticket histories.
- Legal/fachliche final approval of generated knowledge.

## User-visible behavior

### Project lifecycle

A user can create a project by providing at least a project name. The system assigns a stable `project_id` and creates isolated persistence boundaries for that project. The user can reopen/list existing projects, rename a project, and delete a project.

Deleting a project requires explicit confirmation and removes project-scoped database rows and project-scoped artifact files/volume paths. Deletion is not required to be reversible in MVP 1.

The project overview places a compact create-project section above the project list.
Each project row shows only the project name and the locally formatted `updated_at`
date/time; the complete keyboard-accessible row opens the project. Rename remains
available after opening the project. Import precedes Profiles and is the initially
active project tab.

### Import workflow

A user opens a project and imports CSV or JSON. CSV must contain headers matching
`ticket_id`, `message_group_id`, `message`, and `answer`. JSON must be a list of
objects with equivalent keys. The importer validates each record independently.
Legacy `ticketid` and `messagegroupid` inputs are rejected without aliases.

Files through 512 MiB (536,870,912 bytes) are uploaded and parsed as bounded
streams. Larger files are rejected before parsing; backend byte counting remains
authoritative even when the browser has performed a size preflight. Valid records
are persisted as a new dataset version in bounded batches. Invalid records are
counted completely; at most the first 100 skipped-record details are persisted and
returned with source location, reason, and bounded context, and the UI states when
details are truncated. If no valid records remain, or the file-level format is
invalid, no dataset version is created and the actionable failure remains visible.
Temporary upload data is removed on every outcome.

### Analysis-profile workflow

A project can contain multiple analysis profiles. Provider connection settings are configured globally. Each profile selects one globally configured provider/model and stores analysis parameters. A profile can select OpenAI, Ollama, or vLLM models. Provider/model selection is explicit; the system does not silently switch to OpenAI.

OpenAI API keys must not be returned in plaintext-readable form once stored. The UI may show presence/status and allow replacement/removal. Ollama and vLLM global configuration must include endpoint settings and model-discovery or manual model-list behavior sufficient to make exposed local models selectable in analysis profiles.

The profile name field is prefilled per project with `analysis-1` and then one above
the highest existing `analysis-N`; other manually chosen names do not affect that
counter. The suggestion remains editable and server-side project-name uniqueness
remains authoritative. Provider selection filters a model dropdown from that
provider's stored `manual_models`; an empty list blocks profile creation.
Profiles have no Prompt-ID field in the UI, public contract, domain, persistence, or
run snapshot. The separate optional prompt-template capability remains unchanged.

The algorithm dropdown exposes exactly HDBSCAN and Agglomerative because both are
executed by the backend. HDBSCAN fields are `min_cluster_size` (default 5),
optional `min_samples`, and `cluster_selection_epsilon` (default 0). Agglomerative
fields are either `n_clusters` (default 2) or `distance_threshold`, plus `linkage`
(default `ward`). Mutually exclusive and algorithm-specific fields are enforced by
the service and preserved in the run snapshot.

### User management workflow

The application requires sign-in. Users are equal-permission users, not role-separated administrators. Each user has first name, last name, email, and password hash. The email address is used as the login identifier. Any signed-in user can create another user, edit another user's name/email, set or change another user's password, and delete another user. A user cannot delete themselves.

The initial user is created once through environment variables, local configuration, or database migration/seed. Passwords are never stored as plaintext; only password hashes are persisted. Auditable actions persist the acting user identity.

The persisted, domain, and public API user models have no separate username.
Authentication and user-management requests and responses use only `email`;
`username` request fields are rejected. The decision owner explicitly accepted this
breaking contract because the application had no productive use or compatibility
consumer before the change.

The browser stores only the bearer token in tab-scoped session storage. On
application start, a stored token is validated through the authenticated `me`
contract before protected content is displayed; the returned server identity, never
client-persisted user data, owns the restored user state. Missing, invalid, expired,
revoked, or deleted-user sessions return to sign-in and clear the stored token.
Explicit sign-out uses the existing server revocation contract and clears local
session state even when that request fails. Reload persistence is bounded by browser
tab lifetime and the unchanged twelve-hour server-side session expiry.

### Analysis-run workflow

A user starts an analysis run by selecting a dataset version and analysis profile. A
run using OpenAI requires an explicit cloud-use confirmation immediately before
start. There is no user-configurable Run-Modus and the generic run parameter object
must reject a key named `mode`. The selected provider/model generates embeddings
for the `message` text of every pair. Long messages are split at Unicode-safe
boundaries into chunks of at most 1,024 UTF-8 bytes. Chunk generation is incremental,
and only the current provider batch of at most 64 plus fixed-size per-message
accumulators is retained. Multiple chunk vectors are combined through a byte-weighted
mean followed by L2 normalization; a one-chunk provider vector remains unchanged.
The result is exactly one persisted vector per source pair. OpenAI uses its fixed cloud
API host; Ollama and vLLM accept only reviewed local hosts, reject URL credentials,
and do not follow redirects. Provider/model fallback is forbidden.

The run executes in the background and exposes status/progress. Progress starts at
5 when execution begins, advances monotonically after each successfully validated
provider embedding batch through at most 95, and reaches 100 only for a completed
run. A bounded prepass counts provider batches through a server-side cursor that
transfers at most the current 64-message block. That cursor is closed before a
second server-side cursor streams the embedding pass, so neither pass materializes
the complete result set or changes the atomic embedding transaction. A failure
preserves the last confirmed value below 100. Opening the visible Runs tab
loads the current project's run list immediately and then every two seconds without
overlapping requests. Polling stops when the view or project changes, the session
ends, the document becomes hidden, or the component unmounts; returning to a visible
Runs tab refreshes immediately. Stale responses from a previous project, session, or
view cannot replace current state. A transient polling failure retains the last
successful list and later successful polls recover normally.

Provider responses are bounded and validated for count, dimensions, finite numeric
values, and source mapping before vectors are persisted. Ollama embedding requests
set a bounded five-minute keep-alive so the selected model remains warm between
immediately consecutive batches; OpenAI and vLLM request contracts are unchanged.
Two fixed local workers consume an eight-entry queue. Queue overload marks the new
run failed and returns HTTP 503 so the caller can retry. Timeouts, batches, response
size, and memory are bounded.
Errors and diagnostics do not include secrets, raw source text, or raw provider
response bodies. Failure persists a safe actionable reason, including a recognized
context-window violation, and no partial embeddings or clustering state. Successful
embedding metadata records the source byte count, source chunk count, and pooling
method for traceability.

HDBSCAN or Agglomerative consumes the persisted `message` vectors and persists real
labels, outlier/membership state, scores, selected algorithm, parameters, and
provenance. Agglomerative is limited to 10,000 records per run; larger requests fail
before cluster writes and instruct the user to select HDBSCAN. Both algorithms
preflight a conservative 512 MiB total vector/estimator working-set budget before
loading vectors. Pgvector values are decoded through the native Psycopg adapter
directly into a contiguous numerical matrix without a complete text/split-string/
Python-float-list copy. The estimate includes every simultaneously retained native
matrix, estimator, neighbor, label, probability, and mapping representation with
safety headroom. For HDBSCAN it also uses the effective neighbor count from
`min_samples` or, when omitted, `min_cluster_size`, and rejects a neighbor count
above the run size. Agglomerative additionally budgets a bounded nearest-neighbor
workspace, the symmetrized graph/LIL/heap peak, Ward moment matrices, and the two
edge-by-dimension fancy-index copies plus the equally sized subtraction intermediate
used by non-Ward linkages. A disconnected neighbor graph is rejected before the
estimator so scikit-learn cannot construct unbudgeted component-bridging distances.
A rejected request reports safe concrete record, dimension, estimated-byte, and
limit information with a corrective suggestion before cluster writes. No
implementation may construct a complete pairwise all-record distance matrix.

### Curation workflow

A user can inspect generated clusters, source records, analysis variants, scores, categories, and memberships. Automatic values remain stored separately from manual overrides. Effective values are derived from manual overrides where present, otherwise automatic values. Later analysis runs must not overwrite manual curation state unless explicit reset/reapply behavior is added.

### Export workflow

A user exports curated candidates and source assignments to CSV. Export metadata is stored in the project database. Exports that include original text must indicate that original/potentially identifying text is included.

## MVP UI Screens And Workflows

The MVP UI must make the following workflows available without direct database access
or code edits. After sign-in, a persistent sidebar owns global navigation between
Projects and Settings. Project workflows and the provider/user settings use local
tabs. Exact component implementation remains an implementation decision, but all
listed screens, actions, states, and safety prompts are product requirements.

### UI-01 Sign-In

Required elements:

- Email field.
- Password field.
- Sign-in action.
- Error state for invalid credentials.
- Error state for unavailable backend/database.

Rules:

- Unauthenticated users cannot access protected application screens.
- The UI must not reveal whether email or password was the invalid part.
- A valid tab-scoped session survives page reload after server validation.
- Protected screens remain hidden while a stored session is being validated.
- Explicit logout revokes the server session where reachable and always clears the
  local browser session.

### UI-02 User Management

Required elements:

- List of users with first name, last name, and email.
- Create-user action.
- Edit-user action for first name, last name, and email.
- Set/change-password action for another user.
- Delete-user action for another user.
- Disabled or blocked self-delete action with explanatory message.

Rules:

- Password values are write-only in the UI.
- Deleting a user requires confirmation.
- User-management actions must surface success/failure and be auditable.

### UI-03 Global Provider Settings

Required elements:

- OpenAI provider section with API-key set/replace/remove behavior.
- OpenAI key presence/status indicator without showing the key.
- OpenAI model discovery or manual model configuration.
- Ollama provider section with endpoint configuration and model discovery or manual model configuration.
- vLLM provider section with endpoint configuration and model discovery or manual model configuration.
- Provider connection-test action where technically possible.

Rules:

- Provider settings are global, not project-scoped.
- Secrets are never displayed after save.
- Connection/model-list failures must be visible and actionable.

### UI-04 Project Home

Required elements:

- List/open existing projects.
- Create project.
- Rename project.
- Delete project with confirmation.
- Current project summary after opening.

Project summary should show:

- Project name.
- Latest dataset version/import status.
- Existing analysis profiles.
- Latest analysis runs and statuses.
- Candidate/export counts when available.

Rules:

- Project delete is destructive and must require confirmation.
- Project-scoped data from other projects must not appear in the current project view.
- Project creation is compact above the list and does not stretch with list height.
- Project rows contain only name and local last-updated date/time and are fully
  keyboard accessible.
- Import is ordered before Profiles and is active when a project opens.

### UI-05 Project Analysis Profiles

Required elements:

- List profiles in the current project.
- Create/edit profile.
- Select model from globally configured OpenAI/Ollama/vLLM models.
- Use an editable project-local `analysis-N` name suggestion.
- Select HDBSCAN or Agglomerative and show only its valid parameters.
- Configure thresholds and prompt templates where applicable.
- Indicate whether selected model is cloud or local.

Rules:

- Starting an analysis with an OpenAI model must clearly indicate cloud use before execution.
- Starting an analysis with an OpenAI model requires explicit cloud confirmation.
- A profile snapshot must be used for each run so later profile edits do not change historical run metadata.
- Prompt-ID is not an available profile field and is not included in snapshots.

### UI-06 Import

Required elements:

- Select CSV or JSON import file.
- Show required source fields: `ticket_id`, `message_group_id`, `message`, `answer`.
- Show the 512 MiB maximum before submission.
- Start import into the current project.
- Import result summary.
- Link/detail view for persisted import log.

Import summary must show:

- Total records read.
- Valid records imported.
- Skipped records.
- Fatal file-level parse/header errors.
- Dataset version created, if any.

Rules:

- CSV files missing required headers fail before dataset creation.
- Malformed JSON and non-list JSON roots fail before dataset creation.
- Unsupported type, oversize, invalid UTF-8, missing headers, malformed CSV/JSON,
  and wrong JSON root each show a specific actionable German message.
- Invalid records are skipped and logged.
- Complete counts are shown; skipped-record detail is limited to the first 100 and
  labeled when truncated.
- Duplicate `ticket_id` + `message_group_id` records are accepted unless another validation rule fails.
- If zero valid records remain, no dataset version is created and the failure is clearly shown.

### UI-07 Run Monitor

Required elements:

- Start analysis run by selecting dataset version and analysis profile.
- List analysis runs for the current project.
- Show run status: queued, running, completed, failed, cancelled if implemented.
- Show progress where available.
- Show provider/model, dataset version, timestamps, and errors.

Rules:

- Failed runs must retain enough information for diagnosis.
- The UI must distinguish completed, failed, and partial/failed states.
- The run form has no Run-Modus field.
- The visible Runs tab refreshes immediately and then every two seconds without
  overlapping requests or requiring a page reload.
- Polling is limited to the active project, authenticated session, visible document,
  and Runs tab; stale responses must not overwrite current context.
- A transient refresh failure keeps the last successful run state and allows later
  refreshes to recover.
- Progress reflects confirmed provider embedding batches, including multiple
  batches produced by chunking one source message. It advances monotonically through
  at most 95 while running and reaches 100 only for completed runs. Failed runs keep
  their last confirmed progress below 100.

### UI-08 Cluster Explorer

Required elements:

- Cluster list/table for the selected analysis run.
- Filters for status, language, category, type, score, outlier/unassigned state where available.
- Sort by size, score, title, status where available.
- Cluster detail view.
- Source pair detail view with `ticket_id`, `message_group_id`, `message`, and `answer`.
- Automatic, manual, and effective values visibly distinguished.

Required actions:

- Edit cluster title/category/status where implemented in the current milestone.
- Inspect source records.
- Inspect outliers/unassigned records.

Rules:

- Manual values must be visually distinguishable from automatic values.
- Source traceability must remain one click or one drilldown away from cluster detail.
- Loading clusters is disabled for runs that are not completed. A completed run with
  no persisted clusters shows that clusters must be generated first instead of
  silently retaining an empty explorer.

### UI-09 Candidate Editor

Required elements:

- Candidate list for the current project or selected run.
- Candidate type and status.
- Question/answer fields.
- Alternative questions.
- Parameters and external data dependencies where applicable.
- Source clusters/source assignments.
- Notes.

Required actions:

- Create candidate from cluster where implemented.
- Edit candidate fields.
- Change candidate status.
- Inspect source assignments.

Rules:

- Generated and manually edited candidate fields must remain distinguishable.
- Candidate source traceability must remain visible.

### UI-10 Export

Required elements:

- Export candidate CSV.
- Export source-assignment CSV.
- Select current filters/selection where implemented.
- Toggle/include original text where supported.
- Warning when original/potentially identifying text is included.
- Export history/metadata for the current project.

Rules:

- Exported files must use accepted baseline columns.
- Export metadata must be persisted in the project database.
- Export results must show success/failure and output location where applicable.

### UI-11 Shared Error, Empty, And Loading States

Required states:

- Loading state for long-running data loads.
- Empty state for no projects, no imports, no profiles, no runs, no clusters, no candidates, and no exports.
- Permission/authentication expired state if sessions are implemented with expiry.
- Backend unavailable state.
- Provider unavailable state.
- Validation failure summaries with drilldown where applicable.

Rules:

- Long-running operations must not appear frozen.
- Session validation has an explicit loading state that does not expose protected
  content.
- Every failed UI action shows the concrete server-sanitized API detail or a safe
  action-specific network/HTTP fallback. Errors use visible error styling and
  `role="alert"`; non-error feedback uses `role="status"`.
- Failure messages must not expose secrets, raw support text, or raw provider
  response bodies.

### Optional user stories or journey scenarios

| ID   | Actor           | Trigger or goal     | Expected outcome                                                           | Related criteria       |
| ---- | --------------- | ------------------- | -------------------------------------------------------------------------- | ---------------------- |
| US-1 | Analyst/Kurator | Create/open project | Independent project workspace is available and durable.                    | AC-1, AC-2             |
| US-2 | Analyst/Kurator | Import CSV/JSON     | Valid records become a dataset version; invalid records are logged.        | AC-3, AC-4, AC-5, AC-6 |
| US-3 | Analyst/Kurator | Configure profile   | Profile selects OpenAI, Ollama, or vLLM and stores parameters safely.      | AC-7, AC-8             |
| US-4 | Analyst/Kurator | Run analysis        | Background job persists reproducible analysis outputs.                     | AC-10, AC-11, AC-12    |
| US-5 | Analyst/Kurator | Curate results      | Manual edits are separate, durable, and traceable.                         | AC-13, AC-14           |
| US-6 | Analyst/Kurator | Export              | Candidate and source CSV files are produced and export state is persisted. | AC-15                  |

## Functional requirements

- FR-1: Projects must have stable IDs, names, creation/update timestamps, and lifecycle state.
- FR-2: All project-owned records must include `project_id` directly or through a parent key that enforces project isolation.
- FR-3: Dataset versions must be immutable once created from valid import records.
- FR-4: CSV import must reject files missing required headers.
- FR-5: JSON import must reject malformed JSON and non-list roots.
- FR-6: Per-record required fields are `ticket_id`, `message_group_id`, `message`, and `answer`.
- FR-7: `message` and `answer` must be non-empty after trimming whitespace.
- FR-8: Duplicate `ticket_id` + `message_group_id` values are allowed and must not be skipped solely for duplication.
- FR-9: Import logs must include source type, filename or logical source name, started/completed timestamps, total records, valid records, skipped records, failure status, and skipped-record reasons.
- FR-10: Global provider configurations must store OpenAI, Ollama, and vLLM connection settings independently from analysis profiles.
- FR-11: OpenAI provider configuration must support API-key entry/replacement and basic connection/model-list check where possible.
- FR-12: Ollama and vLLM provider configuration must support endpoint configuration and basic connection/model-list check where possible.
- FR-13: Analysis profiles must be project-scoped and versioned or immutable per run so past runs remain reproducible.
- FR-14: Analysis profiles must select one model from globally configured provider models and store analysis-specific thresholds, prompts, algorithms, and parameters.
- FR-15: Stored secrets must not be exposed by read APIs or UI after creation/update.
- FR-16: Users must authenticate before protected application operations.
- FR-17: User records must store first name, last name, email, and password hash. The email address is the login identifier.
- FR-18: Passwords must be hashed using an established password-hashing algorithm and must never be stored or returned as plaintext.
- FR-19: Any authenticated user must be allowed to create users; edit another user's first name, last name, email; set/change another user's password; and delete another user.
- FR-20: A user must not be allowed to delete themselves.
- FR-21: The system must create the initial user once through environment variables, configuration, or database migration/seed.
- FR-22: Auditable actions must persist the acting user identity.
- FR-23: Analysis runs must reference project, dataset version, analysis profile snapshot, provider/model, parameters, status, timestamps, and errors.
- FR-24: Embeddings must reference project, run/profile/model, source object, vector dimensionality, and creation timestamp.
- FR-25: Vector search/clustering must use pgvector indexes or another non-quadratic approach suitable for large datasets.
- FR-26: Cluster records must preserve automatic labels/scores and effective/manual values separately.
- FR-27: Candidate records must support accepted candidate types and statuses from the export baseline.
- FR-28: Candidate source assignments must link candidates to source pairs and optional clusters/segments.
- FR-29: Export metadata must include export type, filters/selection where applicable, dataset/run references, created timestamp, output filename/path where applicable, and whether original text was included.
- FR-30: Profile names must be suggested independently per project as `analysis-N`;
  manually chosen non-matching names do not advance the counter.
- FR-31: Profile model selection must be limited to the selected provider's persisted
  `manual_models`.
- FR-32: New profiles accept only the typed HDBSCAN or Agglomerative parameter
  contracts; historical profile/run JSON remains readable.
- FR-33: Runs persist one real selected-provider `message` embedding per source pair
  with a non-null finite vector and consistent dimensionality before clustering.
- FR-34: Provider embedding calls are bounded, do not silently retry/fallback across
  providers or models, and fail safely without raw text or secrets in diagnostics.
- FR-35: OpenAI is the only cloud embedding target and requires explicit run
  confirmation; Ollama/vLLM embedding endpoints are restricted to reviewed local
  hosts without credentials or redirects.
- FR-36: Agglomerative rejects runs over 10,000 records before cluster mutation;
  neither algorithm may create a complete pairwise all-record distance matrix.
- FR-37: `ticket_id` and `message_group_id` are the canonical names in import files,
  `message_pairs` persistence, domain models, source-detail APIs, frontend models and
  source-assignment exports. Legacy names are not accepted or emitted.
- FR-38: The authenticated import route accepts a raw streamed CSV/JSON file through
  512 MiB and enforces the limit from actual received bytes; the browser check is
  only an early guard.
- FR-39: Import upload, parsing, validation, and persistence must not buffer the
  whole file or all records; temporary input is removed on every outcome and dataset
  persistence is atomic. One backend process admits at most two active imports,
  rejects excess work with HTTP 503, and aborts an upload after 30 seconds without
  a new chunk or 30 minutes total duration. Persistence batches are limited by both
  record count and encoded-text byte estimate; only one pathological record may
  individually exceed that batch estimate.
- FR-40: Complete import counts are retained, while no more than the first 100
  skipped-record details are persisted/returned and truncation is visible.
- FR-41: Import failures distinguish oversize, unsupported type, invalid UTF-8,
  missing CSV headers, malformed CSV, malformed JSON, non-array JSON root, and zero
  valid records with actionable German UI messages.
- FR-42: Prompt-ID is absent from profile UI/frontend models, profile public
  requests/responses, provider domain/service, active database schema, and new or
  migrated run snapshots. Optional prompt templates remain supported.
- FR-43: The run UI and maintained callers do not create a Run-Modus; the backend
  rejects a `mode` key in generic run parameters, and migrated runs retain all
  parameter keys except `mode`.
- FR-44: Analysis splits each non-empty `message` into Unicode-safe chunks of at
  most 1,024 UTF-8 bytes, embeds at most 64 chunks per provider request, and
  produces chunks incrementally without retaining the complete chunk collection.
  It persists exactly one vector per source pair. Multiple chunk vectors use a
  byte-weighted mean followed by L2 normalization; a one-chunk vector remains
  unchanged. Metadata records source byte count, chunk count, and pooling method.
  Provider failures persist an actionable bounded reason without raw provider
  bodies, source text, or partial embeddings.
- FR-45: Analysis progress advances monotonically from 5 through at most 95 after
  confirmed provider embedding batches, including multiple batches produced by
  chunking one source message; only successful completion sets 100 and failure
  preserves the last confirmed value.
- FR-46: Ollama embedding calls set a five-minute keep-alive and the local Compose
  default matches it; OpenAI/vLLM payloads remain unchanged.
- FR-47: Clustering decodes pgvector natively into a contiguous numerical matrix,
  budgets actual simultaneous native representations under the fixed 512 MiB limit,
  and reports safe concrete capacity details before writes when rejected.
- FR-48: Existing UI action failures preserve server-sanitized API details or use
  safe action-specific fallbacks and are semantically and visually marked as errors.

## Quality and operational requirements

- Security and privacy: No production access. OpenAI use is explicit per analysis
  profile and confirmed before a run sends `message` text. API keys are write-only
  after storage. Ollama/vLLM endpoints are local-only. Passwords are stored only as
  password hashes. Authenticated identity is required. Original text is sensitive.
- Reliability and recovery: Persistent Docker volumes must retain database state across container restarts. Failed jobs and imports must leave inspectable logs. Streamed import temporary files must be removed after success, disconnect, oversize, parse failure, or database failure.
- Performance and capacity: Architecture must support hundreds of thousands of records. Imports through 512 MiB must use bounded streaming, parser collections, database batches, and error detail. Full pairwise all-record distance matrices are prohibited for clustering. PostgreSQL/pgvector indexes should be used for vector similarity where appropriate.
- Accessibility and UX: Central workflows must be available through the UI without
  database access or code edits. Import failures and skipped rows must be visible
  without overwhelming the main UI. Every action failure is concrete, safe, and
  distinguishable by text/live-region semantics as well as color.
- Compatibility and migration: PostgreSQL schema changes require migrations. Docker Compose is the local runtime baseline.
- Observability and support: Imports, analysis jobs, provider checks, exports, and destructive project deletes must emit persisted status/log records suitable for UI display.

## Interfaces, data, and domain rules

- Public interfaces and contracts:
- Analysis-profile requests/responses contain name, provider/model, thresholds,
  typed algorithm settings, and optional prompt template, but no Prompt-ID.
- Analysis-run requests retain their generic parameters object for supported
  controls such as cloud confirmation, but `parameters.mode` is invalid.
- Project import request: raw uncompressed UTF-8 file body on the authenticated
  import route, `Content-Type` of CSV or JSON, and RFC 5987
  `Content-Disposition` filename metadata; the former JSON `content` wrapper is not
  retained.
- CSV import contract: header row with `ticket_id`, `message_group_id`, `message`, `answer`.
- JSON import contract: root list of objects with `ticket_id`, `message_group_id`, `message`, `answer`.
- Candidate export CSV columns: `candidate_id`, `candidate_type`, `status`, `language`, `category_path`, `title`, `canonical_question`, `canonical_answer`, `alternative_questions`, `parameters`, `external_data_dependencies`, `quality_score`, `faq_suitability_score`, `dynamicity_score`, `contradiction_score`, `source_pair_count`, `source_cluster_ids`, `dataset_version_id`, `analysis_run_id`, `created_at`, `updated_at`, `contains_original_text`, `notes`.
- Source-assignment export CSV columns: `candidate_id`, `cluster_id`, `pair_id`, `ticket_id`, `message_group_id`, `message_segment_id`, `source_language`, `customer_message`, `support_answer`, `normalized_customer_message`, `normalized_support_answer`, `assignment_type`, `membership_score`, `is_multi_intent`, `intent_label`, `dataset_version_id`, `analysis_run_id`.

- Data ownership and lifecycle:
- Projects own all imported and derived data.
- Dataset versions are immutable.
- Analysis runs are immutable once terminal, except operational metadata needed to mark failure/cancellation.
- Manual overrides are append/update records that preserve automatic source values.
- Project deletion cascades to project-owned database data and project artifact paths after confirmation.

- Validation and authorization rules:
- MVP has multiple equal-permission users and no differentiated role workflow.
- Mutating/auditable operations record audit metadata with the authenticated actor.
- Import validation is per record after file-level parse/header validation.
- All API/database queries must enforce project scope.

- External integrations:
- OpenAI cloud provider for configured profiles.
- Ollama and vLLM local providers through Docker Compose or configured local endpoints.
- No production/customer operational integrations.

## Test seams and verification decisions

### Primary test seam

- Boundary: backend API/service boundary for authentication, user management, project lifecycle, import, provider/profile configuration, analysis-run metadata, curation persistence, and export generation.
- Behaviors covered: authentication, user CRUD constraints, password-hash behavior, persistence, validation, project isolation, import logs, write-only secret behavior, run metadata, export schemas.
- Why this is stable and representative: these behaviors define product contracts independent of UI layout and internal libraries.

### Secondary seams, only where necessary

- Database migration/schema tests for PostgreSQL/pgvector extension and project-scoped constraints.
- Import parser unit tests for CSV/JSON edge cases.
- Provider adapter tests using local stubs for OpenAI/Ollama/vLLM model discovery and
  embedding behavior, including hostile/malformed responses, timeouts, redirects,
  endpoint restrictions, bounds, and no fallback.
- Authentication/user-management tests for sign-in, user CRUD, password change, no self-delete, and audit actor identity.
- End-to-end UI smoke tests for create project, import fixture, configure profile, start run, inspect status, export.
- Synthetic fixed-vector clustering tests for HDBSCAN and Agglomerative, parameters,
  outliers/memberships, traceability, missing/inconsistent vectors, idempotency,
  10,000-record boundary, and absence of complete pairwise distance construction.

### Seams deliberately avoided

- Private helper functions.
- Internal React component state.
- Exact visual graph layout coordinates.
- Exact clustering membership quality for non-reference real data.
- Live OpenAI calls in mandatory tests.
- Production-like deployment tests.

## Acceptance criteria

- [ ] AC-1: A user can create, open/list, rename, and delete projects through supported interfaces.
- [ ] AC-2: Project isolation is enforced: data created in project A is not returned from project B queries or exports.
- [ ] AC-3: Valid CSV fixture imports into a selected project and creates a persisted immutable dataset version.
- [ ] AC-4: Valid JSON fixture imports with behavior equivalent to CSV.
- [ ] AC-5: Missing CSV headers, malformed JSON, and non-list JSON roots fail before dataset creation and produce an import log.
- [ ] AC-6: Invalid records with missing required fields or empty `message`/`answer`
      are skipped and logged; duplicate `ticket_id` + `message_group_id` records are
      accepted.
- [ ] AC-7: An import with zero valid records creates no dataset version and reports a clear failure summary.
- [ ] AC-8: Global provider settings support OpenAI API-key entry/replacement plus Ollama/vLLM endpoint/model discovery or manual model list.
- [ ] AC-9: A project can contain multiple analysis profiles, each selecting a globally configured OpenAI, Ollama, or vLLM model with independent thresholds/parameters.
- [ ] AC-10: Stored OpenAI API keys cannot be retrieved in plaintext through normal read interfaces.
- [ ] AC-11: Users can sign in with email/password.
- [ ] AC-12: An initial user can be created once from environment/configuration or database migration/seed.
- [ ] AC-13: Any authenticated user can create another user, edit another user's name/email, and set/change another user's password.
- [ ] AC-14: Any authenticated user can delete another user, but cannot delete themselves.
- [ ] AC-15: Stored user passwords are password hashes and cannot be retrieved in plaintext through normal read interfaces.
- [ ] AC-16: Auditable actions persist the acting user identity.
- [ ] AC-17: Docker Compose starts PostgreSQL with pgvector using a persistent volume.
- [ ] AC-18: Docker Compose provides Ollama and vLLM service paths or configurable local endpoints and documents local model runtime behavior.
- [ ] AC-19: Background analysis runs persist status, progress, errors, profile snapshot, dataset version, provider/model, parameters, and timestamps.
- [ ] AC-20: Embeddings/vector records persist with dimensionality, model/profile/run references, and source-object references.
- [ ] AC-21: Clustering implementation avoids full pairwise all-record distance computation and exposes outliers/unassigned records.
- [ ] AC-22: Automatic values, manual overrides, and effective values are distinguishable for clusters and candidates.
- [ ] AC-23: Manual curation remains intact after reopening the project and after creating a later analysis run.
- [ ] AC-24: Candidate/source traceability reaches original imported `ticket_id`,
      `message_group_id`, `message`, and `answer`.
- [ ] AC-25: Candidate CSV export exactly includes the accepted baseline columns.
- [ ] AC-26: Source-assignment CSV export exactly includes the accepted baseline columns.
- [ ] AC-27: Export metadata is persisted in the project database and records whether original text was included.
- [ ] AC-28: The application can complete local fixture workflows without OpenAI by using an Ollama, vLLM-compatible, or stubbed local profile.
- [ ] AC-29: The UI exposes sign-in, user management, global provider settings, project home, analysis profiles, import, run monitor, cluster explorer, candidate editor, and export screens or equivalent workflows.
- [ ] AC-30: The UI prevents access to protected screens before sign-in.
- [ ] AC-31: The global provider settings UI allows OpenAI key replacement/removal without displaying the saved key and allows Ollama/vLLM endpoint/model configuration.
- [ ] AC-32: The import UI shows total, imported, skipped, and failed counts and provides access to the persisted import log.
- [ ] AC-33: The run monitor UI distinguishes queued/running/completed/failed states and shows provider/model, dataset version, timestamps, and errors.
- [ ] AC-34: The cluster explorer UI visibly distinguishes automatic, manual, and effective values and provides drilldown to source records.
- [ ] AC-35: The export UI warns when original/potentially identifying text is included and records export metadata.
- [ ] AC-36: Project rows show only name and local update date/time, open as complete
      keyboard-accessible rows, and project creation remains compact above the list.
- [ ] AC-37: Import is before Profiles and is active when a project opens; rename and
      confirmed delete remain available inside the opened project.
- [ ] AC-38: Profile name suggestions increment `analysis-N` independently per
      project and remain editable.
- [ ] AC-39: Provider selection filters a model dropdown from configured models, and
      the profile form exposes only HDBSCAN/Agglomerative with matching parameters.
- [ ] AC-40: Selected providers generate validated, persisted non-null `message`
      vectors without fallback; OpenAI requires confirmation and Ollama/vLLM stay local.
- [ ] AC-41: Both algorithms execute against persisted vectors and preserve
      algorithm/parameter/label/outlier/membership provenance in clusters and snapshots.
- [ ] AC-42: Agglomerative rejects 10,001 records before writes, while 10,000 reaches
      the algorithm seam; no full pairwise all-record distance matrix is constructed.
- [ ] AC-43: Fresh and already initialized empty databases expose
      `message_pairs.ticket_id` and `message_pairs.message_group_id`; no old columns,
      active domain/API/frontend names or export headers remain.
- [ ] AC-44: CSV and JSON accept only the new canonical names; inputs using only
      `ticketid`/`messagegroupid` fail without creating a dataset.
- [ ] AC-45: Valid CSV and JSON files through 512 MiB use the streamed route without
      whole-file or whole-record-list buffering.
- [ ] AC-46: A request above 512 MiB is rejected from actual received bytes with
      HTTP 413, no import/dataset writes, and a German message stating actual and
      maximum size.
- [ ] AC-47: Unsupported extension/media type, invalid UTF-8, missing CSV headers,
      malformed CSV/JSON, non-array JSON root, and zero valid records each produce a
      specific actionable UI message.
- [ ] AC-48: Late parse/database/disconnect/oversize failures leave no partial
      dataset and remove temporary upload data.
- [ ] AC-49: Counts remain complete; only the first 100 skipped details are
      persisted/returned and the UI states when details are truncated.
- [ ] AC-50: Import persistence uses bounded batches and retains project scoping,
      authentication, dataset versioning, audit, and transactional behavior.
- [ ] AC-51: Prompt-ID is absent from profile UI/API/domain/schema and new run
      snapshots; the migration removes the column and historical snapshot key while
      leaving prompt templates intact.
- [ ] AC-52: Run-Modus is absent from the UI and maintained payloads; new
      `parameters.mode` input is rejected before writes, and migration removes only
      the `mode` key from existing run parameters.
- [ ] AC-53: A synthetic 20,711-character Unicode message completes through the
      shared OpenAI/Ollama/vLLM embedding path without exceeding the configured
      chunk or batch bounds, produces exactly one finite message vector with chunk
      provenance, and a simulated context-window response persists an actionable
      error without provider-body or source-text disclosure.
- [ ] AC-54: A valid tab-scoped bearer session survives page reload only after
      `/api/auth/me` validation; invalid sessions expose no protected content and
      are cleared, while explicit logout attempts server revocation and always
      removes local session state.
- [ ] AC-55: The visible Project → Runs view refreshes immediately and every two
      seconds without overlapping requests; project, session, view, visibility, or
      unmount changes stop or invalidate polling, and transient failures preserve
      the last successful state until recovery.
- [ ] AC-56: A multi-batch run exposes multiple monotone progress values between 5
      and 100; only completion sets 100, while a later failure retains its last
      confirmed value below 100 and safe actionable error.
- [ ] AC-57: Every Ollama embedding request and the local Compose default use the
      accepted five-minute keep-alive without changing OpenAI/vLLM payloads.
- [ ] AC-58: Native pgvector loading allows a fixture that exceeded only the former
      text/Python representation estimate to reach the estimator seam; a truly
      oversized fixture fails before writes with concrete safe capacity details.
- [ ] AC-59: All existing UI action failures display server-sanitized detail or a
      safe action-specific fallback with error color and `role="alert"`.
- [ ] AC-60: Cluster loading is disabled for incomplete runs, and an empty completed
      run explains that clusters have not yet been generated.

## Decisions and accepted assumptions

### Confirmed decisions

- The PDF Lastenheft is the MVP baseline, implemented through milestones.
- Local-first Docker Compose is the MVP runtime.
- PostgreSQL with pgvector is the primary local database.
- Persistent Docker volumes are required for database and other durable stores.
- Projects are independent top-level workspaces.
- Required project lifecycle operations are create, open/list, rename, delete.
- CSV and JSON imports use already-paired records.
- Invalid import records are skipped and logged; zero-valid-record imports fail.
- Provider connection settings are global.
- Analysis profiles are scoped per project, select globally configured models, and can differ within a project.
- OpenAI is the first cloud provider.
- Ollama and vLLM are supported MVP local providers.
- GPU is default for local model/analysis workloads when available; CPU fallback is required.
- Simple user management is in scope; all users are equal-permission users.
- Users can manage other users but cannot delete themselves.
- Initial user creation is via environment/configuration or database migration/seed.
- German is the primary working/output language, but source data is multilingual.
- Export field baselines are accepted.
- Synthetic acceptance fixtures may be created.

### Accepted assumptions

- MVP has no differentiated roles or permissions.
- API keys may be stored in a local secret mechanism or encrypted database field, but read interfaces must never return plaintext.
- Passwords are stored only as hashes using an established password-hashing algorithm.
- Mandatory tests should not require live OpenAI access.
- Exact cluster quality thresholds are user-tuned and should not be hard-coded as universal product guarantees.
- HDBSCAN/Agglomerative parameter defaults, the 10,000-record Agglomerative limit,
  provider embedding scope, and project-local naming rule are accepted.
- The repository-wide breaking rename to `ticket_id`/`message_group_id` is accepted
  without compatibility aliases because no persisted data or compatibility consumer
  exists.
- Streamed raw-body imports through 512 MiB, atomic replacement of the buffered JSON
  upload contract, `ijson` for iterative JSON arrays, and a 100-detail skipped-record
  cap are accepted.
- Prompt-ID and Run-Modus are removed without compatibility aliases; optional prompt
  templates and other run parameters remain.
- Browser reload persistence uses token-only tab session storage and retains the
  fixed twelve-hour server expiry.
- Analysis progress is confirmed-batch based, Ollama uses a five-minute keep-alive,
  and the clustering working-set limit remains fixed at 512 MiB while native vector
  representations replace avoidable text/Python copies.
- Concrete UI failures always mean server-sanitized details or safe action-specific
  fallbacks, never raw exceptions, secrets, support text, or provider bodies.
- The visible Runs tab uses the existing project run-list contract with an immediate
  refresh and a bounded two-second polling interval.

### Rejected alternatives that matter later

- MongoDB as primary database for MVP.
- MongoDB plus separate vector database for MVP.
- Treating imported CSV/JSON as transient file views instead of persisted project data.
- Server deployment in MVP 1.
- Production integrations or production data access.

## Remaining implementation choices

- Exact component styling and responsive breakpoints remain implementation decisions
  constrained by the sidebar and tab hierarchy plus the specified UI workflows.
- Exact provider batch size and timeout remain bounded implementation choices
  verified at the adapter seam.

## External standards references

- No external standards source is adopted in this specification.

## Acceptance status

- Shared understanding confirmed: yes
- Confirmed by: User
- Confirmation date: 2026-07-19
- Durable behavior specification accepted: yes
- Incremental change accepted by: User
- Incremental change confirmation date: 2026-07-25
- Import-field rename accepted by: User
- Import-field rename confirmation date: 2026-07-27
- Browser-session/live-run-status change accepted by: User
- Browser-session/live-run-status confirmation date: 2026-07-27
