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

## Scope

### In scope

- Local Docker Compose runtime with PostgreSQL/pgvector persistence and local Ollama/vLLM provider paths.
- Authentication, equal-permission user management, and acting-user audit metadata.
- Project-scoped data and analysis management.
- CSV and JSON import for already-paired support records with persisted import logs.
- Global OpenAI, Ollama, and vLLM provider configuration with explicit per-profile model selection.
- Background analysis runs with persisted run metadata, embeddings/vector state where practical, clusters, curation state, candidates, exports, and source traceability.
- Manual curation that keeps automatic, manual, and effective values distinguishable.
- Candidate and source-assignment CSV exports with original-text warnings where applicable.
- Synthetic reference fixtures for deterministic acceptance tests.

### Out of scope / non-goals

- Production access or production data interaction.
- Server deployment and production-grade operations.
- Operational FAQ agent for new customer requests.
- Automatic or semi-automatic customer communication.
- Live ticket-system, shop, ERP, shipping, repair, or other production integrations.
- Organization-wide approval workflow or differentiated role/permission system.
- Automatic pair inference from ticket histories.
- Final legal or fachliche approval of FAQ content by the system.

## Constraints

- The first release is local-only and must not require server deployment.
- PostgreSQL with pgvector is the accepted primary database.
- Ollama and vLLM are supported local model providers for MVP 1.
- OpenAI is the required cloud provider for MVP 1.
- The MVP uses already-paired records; it does not infer pairs from full ticket timelines.
- Project lifecycle operations required in MVP 1 are create, open/list, rename, and delete.
- German is the primary working/output language where generation is needed; source data can be multilingual.

## Acceptance and durable behavior

Detailed functional requirements, UI workflows, acceptance criteria, test seams, and accepted decisions are maintained in `docs/specifications/support-knowledge-miner-mvp1.md`.

## References

- Product baseline: `docs/Lastenheft_Support_Knowledge_Miner_v0.1.pdf`
- Specification: `docs/specifications/support-knowledge-miner-mvp1.md`
- Architecture overview: `docs/architecture/overview.md`
- Architecture decisions: `docs/architecture/decisions/`

## Approval

- Owner: User
- Status: accepted
- Date: 2026-07-19
