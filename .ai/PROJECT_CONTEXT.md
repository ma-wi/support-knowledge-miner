# Project context

Keep this document compact. It is a map for agents, not a duplicate of the source code or README.

## Purpose

- Product or service: Local-first Support Knowledge Miner for extracting and curating FAQ/support knowledge from historical paired support messages.
- Primary users: Analyst/Kurator, a fachlich-technischer user who imports data, configures analysis profiles, reviews clusters, curates candidates, and exports results.
- Main outcome: Independent projects persist imported CSV/JSON support pairs, analysis runs, embeddings, clusters, curation state, candidates, exports, and source traceability.
- Explicit non-goals: No production access, no operational FAQ agent, no customer communication, no live ticket/shop/ERP integrations, and no server deployment in MVP 1.

## Technology stack

- Languages: Python 3.13, TypeScript, Bash, SQL.
- Frameworks: FastAPI backend; React 19 with Vite frontend.
- Build system: `uv build` for Python package artifacts; `tsc -b` and Vite for frontend builds.
- Package managers: `uv` for Python, `npm` for frontend.
- Runtime and supported versions: CI-defined Ubuntu environment using `.python-version` and `.node-version`.
- Deployment environment: local Docker Compose only.
- Data stores: PostgreSQL with pgvector; local Docker volumes for database and local model caches.
- External services: Optional OpenAI provider by explicit profile selection; optional local Ollama and vLLM-compatible endpoints.

## Architecture map

- Entry points: `backend/main.py`, `backend/api/app.py`, `frontend/src/App.tsx`, `deployment/docker/compose.yml`.
- Core modules: `auth`, `users`, `audit`, `projects`, `imports`, `providers`, `analysis`, `clusters`, `candidates`, `exports`, `db`.
- Data flow: authenticated user opens project, imports paired records, configures provider/profile, starts analysis scaffold, reviews clusters/candidates, and exports CSV with persisted metadata.
- Trust boundaries: browser to authenticated API, local backend to local PostgreSQL, optional explicit OpenAI/Ollama/vLLM provider calls, local filesystem/Compose volumes.
- Public interfaces: FastAPI `/api/*` routes, React MVP shell, Docker Compose local runtime, `.ai/tools/*` quality gates.
- Generated-code locations: Python build output in `dist/` and `build/`, frontend production output in `frontend/dist/`; these are ignored by agents.
- Critical paths: email-only authentication/session validation and migration, project-scoped queries, import validation, provider secret handling and local Ollama endpoint allow-listing, analysis-run metadata, curation override preservation, export original-text warnings.

See `docs/architecture/overview.md` for the durable architecture description.

## Repository conventions

- Source directories: `backend/`, `frontend/src/`, `deployment/docker/`.
- Test directories: `tests/` for backend/service/API/migration tests; `frontend/src/*.test.tsx` for frontend smoke/component tests.
- Naming conventions: backend domain packages mirror product capabilities; SQL migrations use zero-padded numeric prefixes.
- Error-handling conventions: API routes return clear failure messages without exposing secrets; frontend shows summarized status/errors and import log details.
- Logging and telemetry conventions: MVP uses persisted audit/import/export/run records rather than production telemetry.
- Dependency policy: manifests and lockfiles are mandatory; dependency and vulnerability gates run through `./.ai/tools/check-dependencies.sh` and `verify.sh`.
- Migration policy: migrations are committed SQL files in `backend/db/migrations/` and covered by migration tests.
- Migration smoke: `deployment/docker/scripts/smoke-migrations.sh` executes fresh and stopped-version upgrade paths against an isolated local PostgreSQL container.

## Quality commands

- Locked setup: `./.ai/tools/ci-setup.sh`
- Format check: `./.ai/tools/format.sh --check`
- Lint/static analysis: `./.ai/tools/lint.sh`
- Tests: `./.ai/tools/test.sh`
- Dependency checks: `./.ai/tools/check-dependencies.sh`
- Security checks: `./.ai/tools/security.sh`
- Build/package: `./.ai/tools/build.sh`
- Documentation consistency: `python .ai/tools/check-docs.py`
- Full verification: `./.ai/tools/verify.sh`

## Engineering standards MCP

- Optional server: `engineering-knowledge`
- Availability is controlled by `.ai/project.yaml`.
- Retrieve only targeted guidance when local guidance is insufficient for a concrete standards-sensitive decision.
- Record source identifiers only when guidance materially affects a decision.

## Constraints and known risks

- Legal or compliance constraints: Imported support text can contain personal or sensitive data; original-text exports require explicit warnings.
- Security and privacy constraints: Absolute production-access prohibition; passwords are hashes only; OpenAI keys are encrypted and write-only after save; provider/model selection is explicit.
- Compatibility constraints: MVP runtime is local Docker Compose and CI-defined toolchain only.
- Performance constraints: Clustering must avoid full pairwise all-record distance matrices; deterministic MVP scaffold is not final model quality.
- Operational constraints: No production deployment; local volumes own persistence.
- Known technical debt: Analysis and clustering are deterministic scaffolds suitable for MVP flow verification, not final high-quality LLM output.

## High-value references

- Requirement: `docs/requirements/support-knowledge-miner-mvp1.md`
- Specification: `docs/specifications/support-knowledge-miner-mvp1.md`
- Architecture overview: `docs/architecture/overview.md`
- Architecture decisions: `docs/architecture/decisions/`
- Local runtime: `deployment/docker/README.md`
- Security: `SECURITY.md`

## Bootstrap configuration

- Project name: `Support Knowledge Miner`
- Enabled stacks: `python, react, bash`
- Engineering knowledge MCP: `engineering-knowledge` (enabled)
- Configuration source: `.ai/project.yaml`
