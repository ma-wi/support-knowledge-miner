# Feature specification: Support Knowledge Miner MVP 1

Store accepted specifications at `docs/specifications/<requirement-id>.md` so they remain available after temporary implementation artifacts are removed.

- Requirement ID: support-knowledge-miner-mvp1
- Status: ready-for-implementation
- Requirement source: `docs/requirements/support-knowledge-miner-mvp1.md`
- Discovery artifact, if used: `.ai/work/support-knowledge-miner-mvp1/DISCOVERY.md`
- Decision owner: User
- Last updated: 2026-07-19

## Purpose

Support Knowledge Miner MVP 1 provides a local-first project workspace for importing, analyzing, curating, persisting, reopening, and exporting historical support knowledge extracted from already-paired customer-message/support-answer records. It must preserve source traceability, support global model-provider configuration with per-analysis-profile model selection, provide simple equal-permission user management, and keep project state durable in local persistent storage.

## Existing context and terminology

- Applicable ADRs: ADR-0001, ADR-0002, ADR-0003, ADR-0004, ADR-0005.
- Existing domain terms and definitions:
- `Project`: top-level independent workspace containing all imported data, profiles, runs, curation, candidates, exports, and artifact references.
- `DatasetVersion`: immutable version of imported valid source records within one project.
- `MessagePair`: one already-paired customer message and support answer imported from CSV or JSON.
- `AnalysisProfile`: project-scoped configuration for provider/model, algorithms, prompts, thresholds, and runtime parameters.
- `ProviderConfiguration`: global connection and credential configuration for providers such as OpenAI and vLLM.
- `User`: authenticated local application user with username, first name, last name, email, and password hash.
- `AnalysisRun`: one execution of one analysis profile over one dataset version.
- `Embedding`: persisted vector representation associated with a source text, text variant, segment, cluster, or candidate as applicable.
- `Cluster`: automatically generated grouping of semantically/structurally similar records or derived items.
- `Candidate`: curated support knowledge item such as static FAQ, parameterized FAQ, dynamic case, text block, single case, or not usable.
- `ManualOverride`: user-provided change that supersedes an automatic value while preserving the automatic source value.
- `ImportLog`: persisted report of import outcome, including skipped rows/objects and reasons.
- Existing behavior or constraints: Repository currently contains bootstrap Python/React structure; this specification defines product behavior, not implementation details.
- Terminology conflicts to resolve: The draft Lastenheft referenced MongoDB. Discovery supersedes that: PostgreSQL with pgvector is accepted as the primary database.

## Scope

### In scope

- Project lifecycle: create, open/list, rename, delete.
- Project isolation for all persisted data and artifacts.
- CSV import with source fields `ticketid`, `messagegroupid`, `message`, `answer`.
- JSON import as a list of objects with equivalent fields.
- Import validation, skipped-record behavior, and persisted import logs.
- PostgreSQL with pgvector as primary local database with persistent Docker volume.
- Persistent storage of source text, metadata, datasets, analysis profiles, analysis runs, embeddings/vector data where practical, clusters, curation, candidates, audit/import/export metadata.
- Project-scoped persistent file/volume storage for bulky non-query artifacts such as model caches and generated export files.
- Analysis profiles scoped within projects.
- Global provider configuration for OpenAI API key and vLLM connection/model discovery.
- Analysis-profile model selection from globally configured provider models.
- Simple authentication and equal-permission user management.
- Docker Compose local runtime with PostgreSQL/pgvector and vLLM path.
- GPU-default local runtime with CPU fallback.
- Background analysis job state and reproducibility metadata.
- Scalable clustering foundation that avoids full pairwise all-record distance matrices.
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
- Supporting Ollama in the first local-provider slice.
- Legal/fachliche final approval of generated knowledge.

## User-visible behavior

### Project lifecycle

A user can create a project by providing at least a project name. The system assigns a stable `project_id` and creates isolated persistence boundaries for that project. The user can reopen/list existing projects, rename a project, and delete a project.

Deleting a project requires explicit confirmation and removes project-scoped database rows and project-scoped artifact files/volume paths. Deletion is not required to be reversible in MVP 1.

### Import workflow

A user opens a project and imports CSV or JSON. CSV must contain headers matching `ticketid`, `messagegroupid`, `message`, and `answer`. JSON must be a list of objects with equivalent keys. The importer validates each record independently.

Valid records are persisted as a new dataset version. Invalid records are skipped and written to an import log with source location, reason, and enough context to fix the input. If no valid records remain, the import fails and no dataset version is created, but the import log remains available.

### Analysis-profile workflow

A project can contain multiple analysis profiles. Provider connection settings are configured globally. Each profile selects one globally configured provider/model and stores analysis parameters. A profile can select OpenAI or vLLM models. Provider/model selection is explicit; the system does not silently switch to OpenAI.

OpenAI API keys must not be returned in plaintext-readable form once stored. The UI may show presence/status and allow replacement/removal. vLLM global configuration must include endpoint settings and model-discovery or manual model-list behavior sufficient to make exposed local models selectable in analysis profiles.

### User management workflow

The application requires sign-in. Users are equal-permission users, not role-separated administrators. Each user has username, first name, last name, email, and password hash. Any signed-in user can create another user, edit another user's username/name/email, set or change another user's password, and delete another user. A user cannot delete themselves.

The initial user is created once through environment variables, local configuration, or database migration/seed. Passwords are never stored as plaintext; only password hashes are persisted. Auditable actions persist the acting user identity.

### Analysis-run workflow

A user starts an analysis run by selecting a dataset version and analysis profile. The run executes in the background and exposes status/progress. Completion persists embeddings/vector data, generated clusters, metadata, scores, and run diagnostics. Failure persists error details and partial state only when safe and explicitly marked as partial/failed.

### Curation workflow

A user can inspect generated clusters, source records, analysis variants, scores, categories, and memberships. Automatic values remain stored separately from manual overrides. Effective values are derived from manual overrides where present, otherwise automatic values. Later analysis runs must not overwrite manual curation state unless explicit reset/reapply behavior is added.

### Export workflow

A user exports curated candidates and source assignments to CSV. Export metadata is stored in the project database. Exports that include original text must indicate that original/potentially identifying text is included.

## MVP UI Screens And Workflows

The MVP UI must make the following workflows available without direct database access or code edits. Exact visual design, layout system, and component implementation remain implementation decisions, but all listed screens, actions, states, and safety prompts are product requirements.

### UI-01 Sign-In

Required elements:

- Username field.
- Password field.
- Sign-in action.
- Error state for invalid credentials.
- Error state for unavailable backend/database.

Rules:

- Unauthenticated users cannot access protected application screens.
- The UI must not reveal whether username or password was the invalid part.

### UI-02 User Management

Required elements:

- List of users with username, first name, last name, and email.
- Create-user action.
- Edit-user action for username, first name, last name, and email.
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
- vLLM provider section with endpoint configuration.
- vLLM connection/model discovery or manual model configuration.
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

### UI-05 Project Analysis Profiles

Required elements:

- List profiles in the current project.
- Create/edit profile.
- Select model from globally configured OpenAI/vLLM models.
- Configure algorithm parameters, thresholds, prompts or prompt identifiers where applicable.
- Indicate whether selected model is cloud or local.

Rules:

- Starting an analysis with an OpenAI model must clearly indicate cloud use before execution.
- A profile snapshot must be used for each run so later profile edits do not change historical run metadata.

### UI-06 Import

Required elements:

- Select CSV or JSON import file.
- Show required source fields: `ticketid`, `messagegroupid`, `message`, `answer`.
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
- Invalid records are skipped and logged.
- Duplicate `ticketid` + `messagegroupid` records are accepted unless another validation rule fails.
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

### UI-08 Cluster Explorer

Required elements:

- Cluster list/table for the selected analysis run.
- Filters for status, language, category, type, score, outlier/unassigned state where available.
- Sort by size, score, title, status where available.
- Cluster detail view.
- Source pair detail view with `ticketid`, `messagegroupid`, `message`, and `answer`.
- Automatic, manual, and effective values visibly distinguished.

Required actions:

- Edit cluster title/category/status where implemented in the current milestone.
- Inspect source records.
- Inspect outliers/unassigned records.

Rules:

- Manual values must be visually distinguishable from automatic values.
- Source traceability must remain one click or one drilldown away from cluster detail.

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
- Failure messages must avoid exposing secrets or sensitive raw text unnecessarily.

### Optional user stories or journey scenarios

| ID | Actor | Trigger or goal | Expected outcome | Related criteria |
|---|---|---|---|---|
| US-1 | Analyst/Kurator | Create/open project | Independent project workspace is available and durable. | AC-1, AC-2 |
| US-2 | Analyst/Kurator | Import CSV/JSON | Valid records become a dataset version; invalid records are logged. | AC-3, AC-4, AC-5, AC-6 |
| US-3 | Analyst/Kurator | Configure profile | Profile selects OpenAI or vLLM and stores parameters safely. | AC-7, AC-8 |
| US-4 | Analyst/Kurator | Run analysis | Background job persists reproducible analysis outputs. | AC-10, AC-11, AC-12 |
| US-5 | Analyst/Kurator | Curate results | Manual edits are separate, durable, and traceable. | AC-13, AC-14 |
| US-6 | Analyst/Kurator | Export | Candidate and source CSV files are produced and export state is persisted. | AC-15 |

## Functional requirements

- FR-1: Projects must have stable IDs, names, creation/update timestamps, and lifecycle state.
- FR-2: All project-owned records must include `project_id` directly or through a parent key that enforces project isolation.
- FR-3: Dataset versions must be immutable once created from valid import records.
- FR-4: CSV import must reject files missing required headers.
- FR-5: JSON import must reject malformed JSON and non-list roots.
- FR-6: Per-record required fields are `ticketid`, `messagegroupid`, `message`, and `answer`.
- FR-7: `message` and `answer` must be non-empty after trimming whitespace.
- FR-8: Duplicate `ticketid` + `messagegroupid` values are allowed and must not be skipped solely for duplication.
- FR-9: Import logs must include source type, filename or logical source name, started/completed timestamps, total records, valid records, skipped records, failure status, and skipped-record reasons.
- FR-10: Global provider configurations must store OpenAI and vLLM connection settings independently from analysis profiles.
- FR-11: OpenAI provider configuration must support API-key entry/replacement and basic connection/model-list check where possible.
- FR-12: vLLM provider configuration must support endpoint configuration and basic connection/model-list check where possible.
- FR-13: Analysis profiles must be project-scoped and versioned or immutable per run so past runs remain reproducible.
- FR-14: Analysis profiles must select one model from globally configured provider models and store analysis-specific thresholds, prompts, algorithms, and parameters.
- FR-15: Stored secrets must not be exposed by read APIs or UI after creation/update.
- FR-16: Users must authenticate before protected application operations.
- FR-17: User records must store username, first name, last name, email, and password hash.
- FR-18: Passwords must be hashed using an established password-hashing algorithm and must never be stored or returned as plaintext.
- FR-19: Any authenticated user must be allowed to create users; edit another user's username, first name, last name, email; set/change another user's password; and delete another user.
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

## Quality and operational requirements

- Security and privacy: No production access. OpenAI use is explicit per analysis profile. API keys are write-only after storage. Passwords are stored only as password hashes. Authenticated identity is required for protected operations. Original text is treated as potentially sensitive.
- Reliability and recovery: Persistent Docker volumes must retain database state across container restarts. Failed jobs and imports must leave inspectable logs.
- Performance and capacity: Architecture must support hundreds of thousands of records. Full pairwise all-record distance matrices are prohibited for clustering. PostgreSQL/pgvector indexes should be used for vector similarity where appropriate.
- Accessibility and UX: Central workflows must be available through the UI without database access or code edits. Import failures and skipped rows must be visible without overwhelming the main UI.
- Compatibility and migration: PostgreSQL schema changes require migrations. Docker Compose is the local runtime baseline.
- Observability and support: Imports, analysis jobs, provider checks, exports, and destructive project deletes must emit persisted status/log records suitable for UI display.

## Interfaces, data, and domain rules

- Public interfaces and contracts:
- CSV import contract: header row with `ticketid`, `messagegroupid`, `message`, `answer`.
- JSON import contract: root list of objects with `ticketid`, `messagegroupid`, `message`, `answer`.
- Candidate export CSV columns: `candidate_id`, `candidate_type`, `status`, `language`, `category_path`, `title`, `canonical_question`, `canonical_answer`, `alternative_questions`, `parameters`, `external_data_dependencies`, `quality_score`, `faq_suitability_score`, `dynamicity_score`, `contradiction_score`, `source_pair_count`, `source_cluster_ids`, `dataset_version_id`, `analysis_run_id`, `created_at`, `updated_at`, `contains_original_text`, `notes`.
- Source-assignment export CSV columns: `candidate_id`, `cluster_id`, `pair_id`, `ticketid`, `messagegroupid`, `message_segment_id`, `source_language`, `customer_message`, `support_answer`, `normalized_customer_message`, `normalized_support_answer`, `assignment_type`, `membership_score`, `is_multi_intent`, `intent_label`, `dataset_version_id`, `analysis_run_id`.

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
- vLLM local provider through Docker Compose or configured local endpoint.
- No production/customer operational integrations.

## Test seams and verification decisions

### Primary test seam

- Boundary: backend API/service boundary for authentication, user management, project lifecycle, import, provider/profile configuration, analysis-run metadata, curation persistence, and export generation.
- Behaviors covered: authentication, user CRUD constraints, password-hash behavior, persistence, validation, project isolation, import logs, write-only secret behavior, run metadata, export schemas.
- Why this is stable and representative: these behaviors define product contracts independent of UI layout and internal libraries.

### Secondary seams, only where necessary

- Database migration/schema tests for PostgreSQL/pgvector extension and project-scoped constraints.
- Import parser unit tests for CSV/JSON edge cases.
- Provider adapter tests using local stubs for OpenAI/vLLM connection and model-list behavior.
- Authentication/user-management tests for sign-in, user CRUD, password change, no self-delete, and audit actor identity.
- End-to-end UI smoke tests for create project, import fixture, configure profile, start run, inspect status, export.
- Synthetic fixture-based clustering tests verifying non-quadratic path, outlier marking, and traceability on small deterministic data.

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
- [ ] AC-6: Invalid records with missing required fields or empty `message`/`answer` are skipped and logged; duplicate `ticketid` + `messagegroupid` records are accepted.
- [ ] AC-7: An import with zero valid records creates no dataset version and reports a clear failure summary.
- [ ] AC-8: Global provider settings support OpenAI API-key entry/replacement and vLLM endpoint/model discovery or manual model list.
- [ ] AC-9: A project can contain multiple analysis profiles, each selecting a globally configured OpenAI or vLLM model with independent thresholds/parameters.
- [ ] AC-10: Stored OpenAI API keys cannot be retrieved in plaintext through normal read interfaces.
- [ ] AC-11: Users can sign in with username/password.
- [ ] AC-12: An initial user can be created once from environment/configuration or database migration/seed.
- [ ] AC-13: Any authenticated user can create another user, edit another user's username/name/email, and set/change another user's password.
- [ ] AC-14: Any authenticated user can delete another user, but cannot delete themselves.
- [ ] AC-15: Stored user passwords are password hashes and cannot be retrieved in plaintext through normal read interfaces.
- [ ] AC-16: Auditable actions persist the acting user identity.
- [ ] AC-17: Docker Compose starts PostgreSQL with pgvector using a persistent volume.
- [ ] AC-18: Docker Compose provides a vLLM service path or configurable vLLM endpoint and documents GPU-default/CPU-fallback behavior.
- [ ] AC-19: Background analysis runs persist status, progress, errors, profile snapshot, dataset version, provider/model, parameters, and timestamps.
- [ ] AC-20: Embeddings/vector records persist with dimensionality, model/profile/run references, and source-object references.
- [ ] AC-21: Clustering implementation avoids full pairwise all-record distance computation and exposes outliers/unassigned records.
- [ ] AC-22: Automatic values, manual overrides, and effective values are distinguishable for clusters and candidates.
- [ ] AC-23: Manual curation remains intact after reopening the project and after creating a later analysis run.
- [ ] AC-24: Candidate/source traceability reaches original imported `ticketid`, `messagegroupid`, `message`, and `answer`.
- [ ] AC-25: Candidate CSV export exactly includes the accepted baseline columns.
- [ ] AC-26: Source-assignment CSV export exactly includes the accepted baseline columns.
- [ ] AC-27: Export metadata is persisted in the project database and records whether original text was included.
- [ ] AC-28: The application can complete local fixture workflows without OpenAI by using a vLLM-compatible or stubbed local profile.
- [ ] AC-29: The UI exposes sign-in, user management, global provider settings, project home, analysis profiles, import, run monitor, cluster explorer, candidate editor, and export screens or equivalent workflows.
- [ ] AC-30: The UI prevents access to protected screens before sign-in.
- [ ] AC-31: The global provider settings UI allows OpenAI key replacement/removal without displaying the saved key and allows vLLM endpoint/model configuration.
- [ ] AC-32: The import UI shows total, imported, skipped, and failed counts and provides access to the persisted import log.
- [ ] AC-33: The run monitor UI distinguishes queued/running/completed/failed states and shows provider/model, dataset version, timestamps, and errors.
- [ ] AC-34: The cluster explorer UI visibly distinguishes automatic, manual, and effective values and provides drilldown to source records.
- [ ] AC-35: The export UI warns when original/potentially identifying text is included and records export metadata.

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
- vLLM is the MVP local provider; Ollama is out of scope for first local-provider slice.
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

### Rejected alternatives that matter later

- MongoDB as primary database for MVP.
- MongoDB plus separate vector database for MVP.
- Supporting both Ollama and vLLM in the first local-provider slice.
- Treating imported CSV/JSON as transient file views instead of persisted project data.
- Server deployment in MVP 1.
- Production integrations or production data access.

## Open questions and blockers

- No material blockers remain for planning the first implementation milestone.
- Exact visual layout, component styling, and responsive design remain implementation design decisions constrained by the specified UI workflows and screens.
- Exact clustering algorithm defaults may be chosen during technical design, but must satisfy non-quadratic and traceability requirements.

## External standards references

- No external standards source is adopted in this specification.

## Readiness decision

The implementation agent may begin only when:

- material scope and behavior decisions are resolved;
- acceptance criteria are testable;
- test seams are defined;
- remaining assumptions are explicit and acceptable;
- the user or decision owner has confirmed the specification where required.

- Shared understanding confirmed: yes
- Confirmed by: User
- Confirmation date: 2026-07-19
- Ready for implementation: yes
- Readiness conditions or remaining blockers: None. Milestone task files define implementation sequence.
