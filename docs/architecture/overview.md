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
- The backend rejects non-local database URLs to preserve the production-access prohibition.
- Imported support text and original-text exports are treated as potentially sensitive.

## Analysis And Curation

The MVP includes deterministic local scaffolds for analysis runs, embeddings, clustering, candidate curation, and export behavior. Provider/model selection is explicit per analysis profile. OpenAI use is never implicit and is surfaced as cloud usage in the UI.

Automatic, manual, and effective values remain distinguishable for clusters and candidates. Candidate/source traceability links exports back to imported `ticketid`, `messagegroupid`, `message`, and `answer` values.

## Key Decisions

- ADR-0001: Project-scoped workspace isolation.
- ADR-0002: PostgreSQL with pgvector as primary database.
- ADR-0003: Global provider configuration with analysis-profile model selection.
- ADR-0004: Local Docker Compose runtime with GPU default and CPU fallback.
- ADR-0005: Equal-permission local user management.
