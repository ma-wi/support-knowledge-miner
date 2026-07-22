# Feature discovery: Support Knowledge Miner MVP 1

- Requirement ID: support-knowledge-miner-mvp1
- Status: confirmed
- Facilitator/agent: Codex Planner
- Decision owner: User
- Last updated: 2026-07-19

## Discovery trigger

The draft Lastenheft defines a broad initial product with data import, preprocessing, model execution, clustering, curation, persistence, UI exploration, and export. This is significant work because it establishes core architecture, data boundaries, security/privacy behavior, performance constraints, and the initial MVP release boundary. Direct implementation would risk building incompatible data models, unclear workflows, and untestable acceptance criteria.

## Current shared-understanding summary

Support Knowledge Miner MVP 1 is a local-first analysis and curation tool for historical support message-answer pairs. The primary user is a fachlich-technischer Analyst/Kurator. The top-level work unit is a saved project. Each project is independent and contains its own imported datasets, analysis runs, model/profile choices, generated clusters, curation state, candidates, exports, and persisted analysis artifacts. The tool imports already-paired CSV data with columns `ticketid`, `messagegroupid`, `message`, and `answer` into the selected project and stores imported data in the primary local database. It analyzes mostly anonymized multilingual support text, with German as the primary working language, generates clusters and knowledge candidates, and keeps all automated results manually overridable and traceable to original source pairs.

The first delivery is local, not server-deployed. Docker Compose is the local packaging target and must provide persistent volumes for the primary database and any other required stores/artifacts. PostgreSQL with pgvector is the accepted primary database because it can keep projects, source texts, relational curation state, metadata, and vector search in one local persistent database. A local vLLM model server should be deployable through Docker Compose and configurable to expose multiple models. OpenAI is the first cloud provider and is configured in the UI. A local GPU is available by default with CPU fallback. Future server deployment, production integrations, operational FAQ answering, and direct access to production/customer systems are outside the current boundary.

## Decision tree

| ID | Decision or question | Depends on | Recommended answer | User decision | Status |
|---|---|---|---|---|---|
| D001 | Is the Lastenheft content the intended MVP baseline? | none | Treat it as the MVP baseline, then slice into implementable increments. | Yes, this is the MVP version. | confirmed |
| D002 | Target runtime for first step | none | Local-only development/runtime, no server deployment. | Local first; server deployment later. | confirmed |
| D003 | Local packaging target | D002 | Docker Compose for local app stack. | Docker Compose for local would be preferred. | confirmed |
| D004 | Hardware assumption for local analysis | D002 | Support CPU fallback; design for optional GPU acceleration. | Local GPU is available. | confirmed |
| D005 | Source CSV pair formation | none | CSV already contains paired customer/support messages; no ticket-thread pairing in MVP. | CSV contains pairs. | confirmed |
| D006 | CSV minimum schema | D005 | Accept `ticketid`, `messagegroupid`, `message`, `answer`; map to canonical fields. | Structure is `ticketid`, `messagegroupid`, `message`, `answer`. | confirmed |
| D007 | Privacy posture for imported text | none | Treat text as mostly anonymized but still potentially containing personal names; avoid production systems and make cloud use explicit per profile. | Texts are largely anonymized; some names may remain and are acceptable. | confirmed |
| D008 | Primary language behavior | none | Use German as primary curation/output language, while preserving multilingual source handling and language-aware analysis. | Primarily German; final behavior follows ticket languages, so multilingual. | confirmed |
| D009 | Quality/performance parameter ownership | none | User-configurable thresholds and model/algorithm parameters; product provides defaults but no fixed quality guarantees until reference data exists. | User determines parameters by testing. | confirmed |
| D010 | Authorized decision owner | none | Record the user as authorized decision owner for acceptance. | User is the authorized Decision Owner. | confirmed |
| D011 | MVP persistence boundary | D002 | Use Docker Compose persistent volumes for the primary database and any additional artifact stores. | Confirmed: all required stores use persistent Docker volumes; imported file data, analysis data, embeddings, and exports are stored, not only transient/exported. Concrete database engine is superseded by D019. | confirmed |
| D012 | Cloud model use in MVP | D007 | Allow OpenAI as the first cloud provider configured in the UI; model/profile selection is project-specific. | Cloud models are allowed; initially OpenAI is sufficient; model choice is configured in the application per project/profile. | confirmed |
| D013 | MVP release/milestone slicing | D001 | Split the MVP baseline into reviewable milestones while keeping the PDF as the overall MVP scope. | Releases/milestones are acceptable. | confirmed |
| D014 | Reference dataset for acceptance | D009 | Create a synthetic local fixture covering import, validation, multilingual text, clustering, multi-intent, dynamic cases, and export. | Planner may create synthetic data. | confirmed |
| D015 | Retention/deletion behavior for original and analysis data | D007 | Local project data can be deleted by dataset/run; no archival automation in first slice. | Not yet decided. | open |
| D016 | Authentication/users for local MVP | D002 | Add simple equal-permission user management. Store users with username, first name, last name, email, and password hash. All users can create/edit/delete other users, but a user cannot delete themselves. | Confirmed: simple user management is in scope; all users are equal; users can manage other users; initial user is created once through environment/config/migration; audit stores which user performed each action. | confirmed |
| D017 | Project model | D002 | Treat a project as the top-level independent workspace containing datasets, analysis runs, profiles, curation, candidates, exports, and persisted artifacts. | Confirmed: a dataset/analysis is a project; projects can be created/opened, data imported/analyzed/exported inside them, states can be recalled, and projects are absolutely independent. | confirmed |
| D018 | Local model provider support | D003 | Support vLLM as the local model provider through Docker Compose; it can expose multiple configurable models. | Confirmed: implementing only one local provider is sufficient; vLLM is preferred over Ollama. | confirmed |
| D019 | Primary persistence engine | D011 | Use PostgreSQL with pgvector as the primary local database for projects, source texts, structured analysis state, and embeddings/vector search; keep filesystem volumes only for bulky non-query artifacts such as model caches and generated files. | Accepted by Decision Owner: PostgreSQL + pgvector replaces MongoDB as the primary database. | confirmed |
| D020 | Analysis-profile model selection | D012 | Store provider connection/settings globally; analysis profiles select one of the globally configured provider models and store analysis-specific parameters. | Confirmed: provider/model settings can be configured globally; analysis profiles choose the model. | confirmed |
| D021 | JSON import | D005 | Support JSON import in addition to CSV; JSON is a list of objects matching the CSV source structure. | Confirmed: JSON files should be importable as a list of objects with matching fields. | confirmed |
| D022 | Invalid import row behavior | D005 | Skip invalid rows, persist/report skipped-row details in an import log, and clearly report if all rows were skipped. | Confirmed direction: skip invalid rows and output skipped rows in a log; avoid overfilling the main output if all rows fail. | confirmed |
| D023 | Project lifecycle MVP operations | D017 | Support create, open, rename, and delete. | Confirmed: MVP project lifecycle requires create, open, rename, delete. | confirmed |
| D024 | Local GPU behavior | D004 | Use GPU by default for local model/analysis workloads when available; provide CPU fallback. | Confirmed: GPU by default with CPU fallback. | confirmed |
| D025 | Import duplicate handling | D005 | Do not treat duplicate `ticketid` + `messagegroupid` as invalid by default. Persist duplicates as separate records unless another validation rule fails. | Confirmed: `ticketid` + `messagegroupid` need not be unique and duplicates must not be skipped for that reason. | confirmed |

Allowed status values: `open`, `recommended`, `confirmed`, `deferred`, `not-applicable`.

## Recommended interview order

1. Define milestone boundaries for the accepted MVP baseline.
2. Define acceptance/reference datasets and expected validation outcomes.
3. Define exact model-provider configuration UX and secret handling.
4. Define CSV validation behavior.
5. Define minimum UI workflows for import, analysis run, cluster explorer, curation, and export.
6. Define retention/deletion expectations for local projects, datasets, and runs.
7. Finalize architecture decisions needed before specification.

## Optional user stories or journey scenarios

| ID | Actor | Trigger | Desired outcome | Important alternatives/failures |
|---|---|---|---|---|
| US-1 | Analyst/Kurator | Imports CSV/JSON paired support data | Valid rows become a dataset version; invalid rows are reported with row-level reasons. | Missing required columns, empty text, invalid encoding, malformed JSON. Duplicate `ticketid` + `messagegroupid` is allowed. |
| US-1a | Analyst/Kurator | Creates or opens a project | User resumes a fully independent saved project with its datasets, runs, curation state, model configuration, and exports. | Wrong project selected, project missing/corrupt, project deletion/export/import later. |
| US-2 | Analyst/Kurator | Starts an analysis profile on a dataset | Background analysis produces embeddings, clusters, scores, and run metadata without blocking the UI. | Provider/model unavailable, job failure, insufficient GPU/CPU resources. |
| US-3 | Analyst/Kurator | Reviews clusters | User filters/sorts clusters, inspects original messages/answers, and edits titles, categories, memberships, and status. | Outliers, low-confidence clusters, multilingual content, duplicate answers. |
| US-4 | Analyst/Kurator | Adjusts thresholds | User previews impact and saves a new run/snapshot without overwriting manual curation. | Parameter produces too many/few clusters; user discards changes. |
| US-5 | Analyst/Kurator | Creates knowledge candidates | User converts clusters into FAQ/dynamic candidates and traces each candidate back to source pairs. | Conflicting source answers, multi-intent questions, non-generalizable content. |
| US-6 | Analyst/Kurator | Exports curated results | User exports candidates and source assignments as CSV with configurable inclusion of original text. | Export contains original/PII text and must show an explicit warning. |

## Confirmed decisions

- The Lastenheft draft is the intended MVP baseline.
- First runtime target is local execution; server deployment is deferred.
- Docker Compose is the preferred local packaging approach.
- The primary database and any additional stores are provided locally through Docker Compose with persistent volumes.
- PostgreSQL with pgvector is the accepted primary database.
- Any additional stores required for indexes, model caches, or export artifacts must also use persistent Docker volumes or equivalent local persistent storage.
- A local GPU is available and should be considered for local model execution.
- CSV and JSON imports receive already-paired records; the MVP does not need to infer pairs from ticket timelines.
- Minimum CSV source structure is `ticketid`, `messagegroupid`, `message`, `answer`.
- JSON imports use a list of objects with the same logical source fields as CSV.
- Imported files are stored in the selected project and persisted in the primary database as project data.
- Text is already largely anonymized; remaining names can exist, but the system must still treat input as potentially sensitive.
- German is the primary working/output language, while source data and analysis must support multiple languages.
- Quality and threshold parameters are tuned by the user through testing; the system must expose configurable profiles and defaults.
- The MVP baseline may be implemented through releases/milestones rather than one large implementation batch.
- Cloud models are allowed in the MVP; OpenAI is sufficient as the first cloud provider and must be configurable in the UI.
- Provider connection settings are global; analysis profiles choose from globally configured provider models.
- Provider connection settings, such as OpenAI API key and vLLM connection settings, are configured globally.
- Analysis profiles select a globally configured provider/model and store analysis-specific parameters; the model is chosen in the application UI, not automatically.
- vLLM is the selected local model provider for the MVP and should be available through Docker Compose with multiple configurable exposed models.
- Projects are the top-level isolation boundary; projects can be created/opened and each project has independent datasets, analyses, curation, candidates, exports, and stored artifacts.
- MVP project lifecycle operations are create, open, rename, and delete.
- Simple user management is in scope: users have username, first name, last name, email, and password hash; all users have equal permissions.
- Each user can create, edit, delete, and reset/change passwords for other users; a user cannot delete themselves.
- An initial user is created once through environment/configuration or database migration/seed.
- User actions are audited with the acting user.
- Data is persisted to the primary database in addition to any CSV export.
- Invalid import rows are skipped and captured in an import log; duplicate `ticketid` + `messagegroupid` is not invalid by itself; if all rows are skipped, the user receives a clear failure summary.
- The proposed export field baseline is accepted.
- A synthetic reference dataset may be created for deterministic acceptance tests.
- The user is the authorized Decision Owner.

## Rejected alternatives

- Building an operational FAQ agent for new customer requests in this MVP.
- Sending automatic or semi-automatic answers to customers.
- Integrating live ticket/shop/ERP/shipping/repair systems in the first step.
- Inferring message-answer pairs from full ticket histories for the initial CSV import path.
- Server deployment as an initial requirement.
- Treating CSV import as a transient file-only operation without persistence.
- Supporting both Ollama and vLLM in the first local-provider slice.

## Assumptions accepted for planning

- All development, tests, and demos use local/dev/test/sandbox data only, with no production access.
- The MVP has authentication and simple user administration, but no differentiated roles or permissions.
- The primary database runs locally through Docker Compose unless the Decision Owner later approves another non-production target.
- Raw embeddings and vector indexes are stored in PostgreSQL/pgvector where practical; model caches and generated files may use project-scoped persistent Docker volumes.
- Local-only model execution should be possible even when OpenAI cloud profiles are available.
- Defaults may be heuristic; acceptance of clustering quality requires explicit reference data or qualitative review criteria.

## Open questions and blockers

- OQ-01: Define how global OpenAI and vLLM provider configuration is represented in the UI, including secret handling for the OpenAI API key and model discovery/refresh behavior.
- OQ-02: Define exact CSV/JSON validation behavior for missing answers, multiline text, delimiters, encodings, malformed JSON, and non-list JSON roots. Duplicate `ticketid` + `messagegroupid` is allowed.
- OQ-03: What data deletion/retention behavior is required for local original texts, normalized/anonymized variants, embeddings, and analysis runs when a project is deleted?
- OQ-04: Which UI workflows are mandatory in milestone 1: import wizard, run monitor, cluster table, detail pane, graph, candidate editor, export?
- OQ-05: Confirm NVIDIA CUDA container runtime as the GPU path for local Docker Compose, with CPU fallback.

## Proposed export schemas

### Candidate export CSV

Recommended columns:

- `candidate_id`
- `candidate_type` (`static_faq`, `parameterized_faq`, `dynamic_case`, `text_block`, `single_case`, `not_usable`)
- `status` (`unreviewed`, `in_progress`, `reviewed`, `rejected`, `export_ready`)
- `language`
- `category_path`
- `title`
- `canonical_question`
- `canonical_answer`
- `alternative_questions`
- `parameters`
- `external_data_dependencies`
- `quality_score`
- `faq_suitability_score`
- `dynamicity_score`
- `contradiction_score`
- `source_pair_count`
- `source_cluster_ids`
- `dataset_version_id`
- `analysis_run_id`
- `created_at`
- `updated_at`
- `contains_original_text`
- `notes`

### Source assignment export CSV

Recommended columns:

- `candidate_id`
- `cluster_id`
- `pair_id`
- `ticketid`
- `messagegroupid`
- `message_segment_id`
- `source_language`
- `customer_message`
- `support_answer`
- `normalized_customer_message`
- `normalized_support_answer`
- `assignment_type` (`automatic`, `manual`, `effective`)
- `membership_score`
- `is_multi_intent`
- `intent_label`
- `dataset_version_id`
- `analysis_run_id`

### Optional later exports

- Cluster export CSV with cluster metadata, labels, scores, categories, and counts.
- Audit export CSV with manual override history.
- Analysis-run export JSON with profile, parameters, model/provider metadata, prompts, and algorithm configuration.

## Proposed scope

### In scope

- Local-first application stack suitable for Docker Compose.
- Project management for creating/opening saved independent projects.
- CSV import of already-paired records using `ticketid`, `messagegroupid`, `message`, `answer`.
- Canonical internal data model preserving original text and separate analysis variants.
- Primary local database with a persistent Docker volume for structured project entities: projects, datasets, source pairs, text variants, analysis profiles/runs, embeddings, vector indexes when supported, clusters, curation, candidates, audit events, and export metadata.
- PostgreSQL with pgvector is the accepted primary database architecture.
- Local persistent Docker volumes for additional artifact stores if they are inefficient to store directly in the primary database, such as cached model files, generated export files, or large batch artifacts.
- Language detection and multilingual-safe storage/display, with German as primary curation/output language.
- Global UI-configurable provider settings for OpenAI and vLLM.
- UI-configurable analysis profiles with selected model, algorithm, threshold, prompt, and parameter metadata.
- Local model server through Docker Compose, targeting vLLM with multiple configurable exposed models.
- Local-only analysis path plus OpenAI cloud provider support through explicit project/profile model selection.
- Scalable clustering approach that avoids full pairwise all-record distance matrices.
- Manual curation layer preserving automatic values separately from overrides.
- Traceability from candidates/clusters back to original message-answer pairs.
- CSV and JSON import of already-paired source data.
- CSV export of candidates and source assignments.

### Out of scope / non-goals

- Production access or production data interaction.
- Server deployment, multi-tenant operations, and production-grade ops automation.
- Live ticket-system, shop, ERP, shipping, repair, or customer communication integration.
- Operational FAQ answering for new incoming requests.
- Organization-wide approval workflow or differentiated roles/permissions.
- Legal/fachliche final approval of FAQ content by the system.
- Automatic pair inference from ticket histories in the first CSV path.
- Production-grade model-serving operations beyond local Docker Compose.
- Multiple local model-server implementations in the first slice; vLLM is sufficient.

## Draft success and acceptance criteria

- [ ] A local CSV fixture with columns `ticketid`, `messagegroupid`, `message`, and `answer` imports into a versioned dataset with row-level validation results.
- [ ] A local JSON fixture containing a list of objects with `ticketid`, `messagegroupid`, `message`, and `answer` imports with equivalent validation behavior.
- [ ] The user can create and reopen independent projects; each project preserves its imported data, analysis runs, curation state, candidates, exports, and model/profile settings.
- [ ] The user can rename and delete projects.
- [ ] Invalid CSV rows or JSON objects with missing required fields or empty text are skipped and captured in an import log according to the accepted validation rules; duplicate `ticketid` + `messagegroupid` records are accepted.
- [ ] A local analysis profile records model/provider, algorithm, metrics, prompts where applicable, thresholds, and runtime parameters for each analysis run.
- [ ] The UI can configure global OpenAI credentials and global vLLM provider endpoints/models without storing API keys in plaintext-readable form.
- [ ] Analysis profiles select from globally configured models and store analysis-specific parameters.
- [ ] Users can sign in; create, edit, delete, and reset/change passwords for other users; cannot delete themselves; and actions are audited with acting user identity.
- [ ] Docker Compose provides the primary database with persistent volume and vLLM provider service or endpoint sufficient for MVP development/testing.
- [ ] Analysis runs execute as background jobs with status, progress, errors, and reproducible run metadata.
- [ ] Embeddings and other required analysis artifacts are persisted and reusable when reopening a project.
- [ ] Clustering supports a non-quadratic approach suitable for hundreds of thousands of pairs and exposes outliers.
- [ ] The user can inspect clusters, original messages, answers, analysis variants, scores, categories, and memberships.
- [ ] Automatically generated titles/categories/candidates are stored separately from manual overrides.
- [ ] Manual overrides survive a new analysis run unless explicitly reset or reapplied by accepted rules.
- [ ] Each cluster/candidate can be traced back to original message-answer pairs.
- [ ] CSV exports for curated candidates and source assignments include dataset/run references and warn when original or potentially identifying text is included.
- [ ] Exported data is also represented in the primary database as project export metadata/state, not only written as files.
- [ ] The application can run locally without cloud model providers.
- [ ] Docker Compose starts the local app services required for MVP development/testing.

## Shared-understanding confirmation

Before moving to an accepted implementation plan, present the current summary, confirmed decisions, scope, assumptions, and open questions to the user.

- User explicitly confirmed shared understanding: yes
- Confirmed by: User
- Confirmation date: 2026-07-19
- Corrections or conditions: Continue to durable requirements and specification; PostgreSQL with pgvector accepted as the primary database.

Do not implement until the value above is `yes`.
