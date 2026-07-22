# Requirement: Support Knowledge Miner MVP 1

## Problem

Historical support data contains recurring customer questions, reused answer patterns, implicit categories, multi-intent cases, and dynamic support cases. The data is currently unstructured and difficult to inspect, cluster, curate, trace, and export as reusable support knowledge.

The MVP must provide a local-first project workspace where an analyst/curator can import already-paired historical support records, analyze them with configurable local or OpenAI models, persist the resulting analysis state, manually curate generated results, and export curated knowledge with source traceability.

## Desired outcome

A user can sign in, manage equal-permission users, create an independent local project, import CSV or JSON message-answer pairs, configure global model providers, select models in analysis profiles, run analysis jobs, persist all project state in local storage, inspect and curate clusters/candidates, and export curated candidate and source-assignment CSV files. Projects can be reopened later with their data, analysis runs, embeddings, curation state, candidates, exports, and profile configuration intact.

## Users and stakeholders

- Primary user: Analyst/Kurator, a fachlich-technischer user who imports data, configures analysis, reviews clusters, curates candidates, and exports results.
- Decision owner: User.
- System operator for MVP: local user running Docker Compose.
- Affected parties: people represented in historical support text. The text is mostly anonymized but may still contain names, so imported text remains potentially sensitive.

## Optional user stories or journey scenarios

- US-1: As an Analyst/Kurator, I want to create or open a project, so that each dataset and analysis state remains independent and reusable.
- US-2: As an Analyst/Kurator, I want to import CSV or JSON paired support records, so that historical support data becomes a versioned project dataset.
- US-3: As an Analyst/Kurator, I want skipped import rows logged, so that data-quality issues are visible without blocking valid rows.
- US-4: As an Analyst/Kurator, I want to configure providers globally and select models per analysis profile, so that different models and thresholds can be tested inside one project without duplicating provider setup.
- US-5: As an Analyst/Kurator, I want analysis outputs persisted, so that projects can be reopened without losing embeddings, runs, clusters, candidates, and curation.
- US-6: As an Analyst/Kurator, I want exportable candidates and source assignments, so that curated knowledge can be reused outside the tool while preserving traceability.
- US-7: As a user, I want to manage other equal-permission users, so that local access can be shared without a role workflow.

## Functional requirements

- FR-1: The system must support creating, opening, renaming, and deleting independent projects.
- FR-2: A project must isolate its datasets, source records, analysis profiles, analysis runs, embeddings, clusters, curation state, candidates, exports, and artifact references from all other projects.
- FR-3: The system must import CSV files containing already-paired records with fields `ticketid`, `messagegroupid`, `message`, and `answer`.
- FR-4: The system must import JSON files containing a list of objects with fields equivalent to the CSV schema.
- FR-5: Imported valid records must be persisted in the selected project, not treated as transient opened files.
- FR-6: Invalid CSV rows or JSON objects must be skipped, captured in a persisted import log, and summarized after import.
- FR-7: If an import contains zero valid records, the import must fail with a clear summary and persisted import log.
- FR-8: The system must support global provider configuration for OpenAI and vLLM.
- FR-9: OpenAI global provider configuration must support storing/replacing an API key without returning it in plaintext-readable form.
- FR-10: vLLM global provider configuration must support storing connection settings and discovering or configuring multiple exposed models.
- FR-11: The system must support analysis profiles scoped to a project.
- FR-12: Each analysis profile must select one globally configured model and define algorithm parameters, thresholds, and generation/classification prompt metadata where applicable.
- FR-13: Model selection must be explicit per analysis profile and must not happen automatically without user configuration.
- FR-14: The system must support OpenAI as the first cloud model provider.
- FR-15: The system must support vLLM as the local model provider through Docker Compose.
- FR-16: The system must provide simple authentication and user management.
- FR-17: Each user must have username, first name, last name, email, and password hash.
- FR-18: All users must have equal permissions.
- FR-19: Any user must be able to create users; edit another user's username, first name, last name, email; set/change another user's password; and delete another user.
- FR-20: A user must not be able to delete themselves.
- FR-21: The initial user must be created once through environment variables, configuration, or database seed/migration.
- FR-22: The system must record which authenticated user performed each auditable action.
- FR-23: The system must persist all analysis-run metadata needed to reproduce or explain a run: dataset version, profile, provider, model identifiers, parameters, algorithm choices, thresholds, timestamps, status, and errors.
- FR-24: Analysis jobs must run as background jobs with observable status, progress, completion, and failure state.
- FR-25: The system must persist embeddings and reusable vector-search state in PostgreSQL/pgvector where practical.
- FR-26: The system must support scalable clustering that does not require a full pairwise distance matrix over all records.
- FR-27: The system must expose outliers or unassigned records.
- FR-28: Automatically generated values, manual overrides, and effective values must remain distinguishable.
- FR-29: Manual curation state must survive reopening a project and must not be overwritten by later analysis runs unless explicit reset/reapply rules are implemented.
- FR-30: Candidates, clusters, and exports must be traceable back to original source records.
- FR-31: The system must export curated candidates as CSV using the accepted candidate export baseline.
- FR-32: The system must export candidate-source assignments as CSV using the accepted source-assignment export baseline.
- FR-33: Export metadata/state must also be persisted in the project database.
- FR-34: The system must support multilingual source data, with German as the primary working/output language where generation is needed.

## Non-functional requirements

- Security: No project/customer/organizational production access is allowed. Passwords must be stored only as password hashes, never plaintext. OpenAI keys must not be stored in plaintext-readable form. Provider configuration must avoid accidental cloud use by requiring explicit profile model selection. Authenticated user identity must be enforced for protected operations.
- Privacy: Imported text must be treated as potentially sensitive even when largely anonymized. Exports that include original text must clearly indicate that original/potentially identifying text is included.
- Performance: The architecture must target several hundred thousand paired records without full pairwise all-record distance computation. GPU should be used by default for local model/analysis workloads when available, with CPU fallback.
- Reliability: Project state must be durable across application restarts through persistent Docker volumes. Background-job failures must be persisted and inspectable.
- Accessibility: MVP UI must support the central workflows without direct database access or code edits.
- Compatibility: Local-first Docker Compose is the MVP runtime. Server deployment is out of scope for MVP 1.
- Operability: Docker Compose must provide PostgreSQL/pgvector and vLLM services or endpoints sufficient for local development/testing. Additional local volumes may store model caches or generated files.

## Constraints

- The first release is local-only and must not require server deployment.
- PostgreSQL with pgvector is the accepted primary database.
- vLLM is the only required local model provider for the MVP.
- OpenAI is the only required cloud provider for the MVP.
- The MVP uses already-paired records; it does not infer pairs from full ticket timelines.
- Project lifecycle operations required in MVP are create, open, rename, and delete.
- The full Lastenheft is the MVP baseline, but implementation may be split into milestones.

## In scope

- Local Docker Compose stack.
- Project-scoped data and analysis management.
- PostgreSQL/pgvector persistence.
- Persistent local artifact storage for non-database artifacts.
- CSV and JSON import.
- Import validation and import logs.
- Analysis-profile provider/model configuration.
- OpenAI provider configuration.
- vLLM provider configuration.
- Background analysis runs.
- Embedding/vector persistence.
- Scalable clustering foundation.
- Manual curation foundation.
- Candidate/source traceability.
- Candidate and source-assignment CSV exports.
- Synthetic reference fixtures for deterministic acceptance tests.

## Out of scope / non-goals

- Operational FAQ agent for new customer requests.
- Automatic or semi-automatic customer communication.
- Live ticket-system, shop, ERP, shipping, repair, or production integration.
- Production access or production data interaction.
- Server deployment and production-grade operations.
- Organization-wide approval workflow or differentiated role/permission system.
- Automatic pair inference from ticket histories.
- Supporting both Ollama and vLLM in the first local-provider slice.
- Final legal or fachliche approval of FAQ content by the system.

## Acceptance criteria

- [ ] AC-1: A user can create, open, rename, and delete local projects.
- [ ] AC-2: Two projects remain isolated: imports, profiles, runs, clusters, curation, candidates, and exports from one project are not visible in the other.
- [ ] AC-3: A valid CSV fixture with `ticketid`, `messagegroupid`, `message`, and `answer` imports into a selected project and creates a persisted dataset version.
- [ ] AC-4: A valid JSON fixture containing a list of matching objects imports with equivalent behavior to CSV.
- [ ] AC-5: Invalid rows/objects are skipped, persisted in an import log with row/object location and reason, and summarized after import.
- [ ] AC-6: An import with zero valid records fails clearly and preserves the import log.
- [ ] AC-7: A project can contain multiple analysis profiles, each selecting a globally configured OpenAI or vLLM model and its own thresholds/parameters.
- [ ] AC-8: OpenAI credentials are not returned in plaintext-readable form after storage.
- [ ] AC-9: Users can sign in, create other users, edit other users, set/change other users' passwords, and delete other users.
- [ ] AC-10: A user cannot delete themselves.
- [ ] AC-11: Stored passwords are password hashes and are not returned in plaintext-readable form.
- [ ] AC-12: An initial user can be created once through environment/configuration or database seed/migration.
- [ ] AC-13: Audited actions persist the acting user identity.
- [ ] AC-14: Docker Compose provides persistent PostgreSQL/pgvector storage and a vLLM service or configurable vLLM endpoint path.
- [ ] AC-15: A background analysis run records status, progress, errors, dataset version, profile, provider/model, algorithm parameters, timestamps, and reproducibility metadata.
- [ ] AC-16: Embeddings/vector data needed by an analysis run are persisted and available after reopening the project.
- [ ] AC-17: Clustering avoids full pairwise all-record distance computation and marks outliers/unassigned records.
- [ ] AC-18: Manual curation state remains distinguishable from automatic results and persists across project reopen.
- [ ] AC-19: Candidates and clusters can be traced back to source records.
- [ ] AC-20: Candidate and source-assignment CSV exports use the accepted baseline fields and persist export metadata in the database.
- [ ] AC-21: The application can run locally without using OpenAI when a local vLLM-compatible profile is selected.

## Available references

- Existing document: `docs/Lastenheft_Support_Knowledge_Miner_v0.1.pdf`
- Discovery: `.ai/work/support-knowledge-miner-mvp1/DISCOVERY.md`
- Workflow: `.ai/policies/WORKFLOW.md`

## Open questions

- Exact milestone boundaries remain to be finalized in the specification and task plan.
- Exact visual UI layout remains implementation design; required MVP UI workflows and screens are specified in `docs/specifications/support-knowledge-miner-mvp1.md`.
- Exact clustering algorithm defaults remain specification-level choices, provided the implementation avoids full pairwise all-record distance computation.

## Approval

- Owner: User
- Status: accepted
- Date: 2026-07-19
