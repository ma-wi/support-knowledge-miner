# Architecture Overview

Support Knowledge Miner MVP 1 is a local-first application with a Python FastAPI backend, React frontend, and PostgreSQL/pgvector persistence. It has no production deployment path and must only be used with local, development, test, or sandbox resources.

## Runtime Components

- `frontend/`: React/Vite MVP shell for authentication, user management, provider/profile configuration, project management, import, run monitoring, cluster exploration, candidate curation, and exports.
- `backend/api/app.py`: FastAPI HTTP boundary. Protected routes require bearer-token session authentication.
- `backend/*/service.py`: domain services for auth, users, audit, projects, imports, providers, analysis runs, clusters, candidates, and exports.
- `backend/db/migrations/`: SQL migrations for PostgreSQL/pgvector schema.
- `deployment/docker/compose.yml`: local PostgreSQL/pgvector plus optional Ollama and vLLM services.

## Data Ownership

`Project` is the top-level isolation boundary. Project-owned records are scoped directly by `project_id` or through a project-scoped parent. Project deletion is destructive after explicit confirmation.

PostgreSQL stores users, sessions, audit events, projects, imports, dataset versions, message pairs, provider configuration metadata, analysis profiles, run metadata, embeddings, clusters, candidates, source assignments, and export logs. pgvector is used for persisted embedding vectors where practical.

## Security Boundaries

- Authentication is required for protected API and UI workflows.
- Passwords are hashed with Argon2id and are never returned through read APIs.
- Session bearer tokens are stored server-side as hashes.
- OpenAI API keys are encrypted at rest and write-only through normal provider read APIs.
- OpenAI embedding runs require explicit cloud-use confirmation and use the fixed
  official API host.
- Ollama and vLLM endpoints are restricted to reviewed local hosts and provider
  requests reject credentials and redirects.
- The backend rejects non-local database URLs to preserve the production-access prohibition.
- Imported support text and original-text exports are treated as potentially sensitive.
- Import requests are raw authenticated CSV/JSON streams capped from actual received
  bytes at 512 MiB. The HTTP boundary owns a permission-restricted local temporary
  file and removes it on every path.

## Bounded Imports

The maintained browser client sends the selected `File` directly with its CSV/JSON
media type and RFC 5987 filename metadata. The existing import service validates a
temporary file in a first sequential pass, then repeats parsing inside the existing
database transaction and writes valid message pairs in batches capped at 1,000
records and a conservative 4 MiB encoded-text estimate. CSV uses the Python
standard library and JSON uses `ijson`; neither path retains the complete file or
record list. Counts cover every record, while persisted and returned skipped-row
details are capped at 100. Dataset creation, message-pair writes, import logging, and
audit recording remain one atomic transaction. A process-local capacity guard admits
at most two active upload/import operations; excess work receives HTTP 503. A
30-second per-chunk idle timeout and absolute 30-minute upload deadline prevent
idle or slow-drip clients from retaining a slot and temporary file indefinitely.

## Analysis And Curation

Analysis runs incrementally split long `message` text at Unicode-safe boundaries
into chunks of at most 1,024 UTF-8 bytes and retain at most the 64 chunks needed for
the current call through the explicitly selected OpenAI, Ollama, or vLLM model.
A byte-weighted mean followed by L2
normalization combines multiple chunk vectors into exactly one validated persisted
pgvector value per source pair; a one-chunk provider vector stays unchanged.
Chunk count, source byte count, and pooling method provide non-text provenance.
Two fixed local workers consume an eight-entry in-memory queue; overload
marks the just-created run failed and returns a retryable service-unavailable
response. HDBSCAN and Agglomerative consume persisted vectors only after a
conservative 512 MiB input/estimator working-set preflight. Agglomerative is limited
to 10,000 records and uses a bounded nearest-neighbor graph. The preflight includes
the preallocated native float32 matrix, estimator matrices, bounded binary fetch
batch and nearest-neighbor workspace, linkage-specific graph/intermediate
structures, results/mappings, and conservative per-record overhead. HDBSCAN
additionally budgets the distance/index arrays implied by its effective
`min_samples` value. Agglomerative rejects disconnected neighbor graphs before
estimator execution rather than allowing unbounded component-distance completion.
Algorithm, parameters, labels, scores, memberships, outliers, provider, and model
provenance remain persisted. Candidate curation and export retain their MVP workflow
seams.

Automatic, manual, and effective values remain distinguishable for clusters and candidates. Candidate/source traceability links exports back to imported `ticket_id`, `message_group_id`, `message`, and `answer` values.

## Key Decisions

- ADR-0001: Project-scoped workspace isolation.
- ADR-0002: PostgreSQL with pgvector as primary database.
- ADR-0003: Global provider configuration with analysis-profile model selection.
- ADR-0004: Local Docker Compose runtime with GPU default and CPU fallback.
- ADR-0005: Equal-permission local user management.
- ADR-0006: Streamed bounded imports.
