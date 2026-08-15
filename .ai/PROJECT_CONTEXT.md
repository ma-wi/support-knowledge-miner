# Project context

Keep this document compact. It is a map for agents, not a duplicate of the source code or README.

## Purpose

- Product or service: Local-first Support Knowledge Miner for extracting and curating FAQ/support knowledge from historical paired support messages.
- Primary users: Analyst/Kurator, a fachlich-technischer user who imports data, configures embedding providers, starts dataset indexing, reviews/refines Cluster-Sets, inspects sources, and exports Explorer results.
- Main outcome: Independent projects persist imported CSV/JSON support pairs, indexing runs, embeddings, saved Cluster-Sets, cluster summaries, curation state, Explorer exports, and source traceability.
- Explicit non-goals: No production access, no operational FAQ agent, no customer communication, no live ticket/shop/ERP integrations, and no server deployment in MVP 1.

## Technology stack

- Languages: Python 3.13, TypeScript, Bash, SQL.
- Frameworks: FastAPI backend; React 19 with Vite frontend.
- Build system: `uv build` for Python package artifacts; `tsc -b` and Vite for frontend builds.
- Package managers: `uv` for Python, `npm` for frontend.
- Runtime and supported versions: CI-defined Ubuntu environment using `.python-version` and `.node-version`.
- Deployment environment: local Docker Compose only.
- Data stores: PostgreSQL with pgvector; local Docker volumes for database and local model caches.
- Optional GPU runtime: RAPIDS/cuML is available through the mutually exclusive
  `gpu-cu12` or `gpu-cu13` Python extras; default setup remains CPU-compatible.
- External services: Optional OpenAI by explicit per-action confirmation; optional
  local Ollama endpoints. OpenAI/Ollama provider instances expose separate
  embedding and LLM model allow-lists and can be used for bounded Cluster-Set
  summaries when configured. vLLM is not active in the current UI/API/runtime.

## Architecture map

- Entry points: `backend/main.py`, `backend/api/app.py`, `frontend/src/App.tsx`, `deployment/docker/compose.yml`.
- Core modules: `auth`, `users`, `audit`, `projects`, `imports`, `providers`, `analysis`, `clusters`, `exports`, `db`.
- Data flow: authenticated user opens a project, imports paired records, chooses
  a configured embedding provider/model for dataset indexing, persists bounded
  provider embeddings for `message` and `answer` text, creates saved Cluster-Sets
  from completed Indizierungen with selectable vector basis and parameters, can
  optionally generate bounded LLM summaries, curates Cluster-Set rows in the
  Explorer, inspects source dialogs, refines child Cluster-Sets, and exports the
  current Explorer table state as CSV/JSON.
- Trust boundaries: browser to authenticated API, local backend to local
  PostgreSQL, optional explicit per-indexing OpenAI/Ollama embedding provider
  calls, optional per-Cluster-Set OpenAI/Ollama LLM calls, local filesystem/Compose
  volumes.
- Control plane: `.ai/tools/orchestrate.py`; policy:
  `.ai/policies/ORCHESTRATION.md`
- Public interfaces: FastAPI `/api/*` routes, React MVP shell, Docker Compose local runtime, `.ai/tools/*` quality gates. Persisted Cluster-Set routes own clustering; obsolete run-bound cluster routes return 410 replacement Problem Details.
- Generated-code locations: Python build output in `dist/` and `build/`, frontend production output in `frontend/dist/`; these are ignored by agents.
- Critical paths: email-only authentication with server-validated tab-scoped
  session restoration and explicit revocation, project-scoped queries,
  two-slot/30-second-idle/30-minute-total-capped 512 MiB import spooling, two-pass import
  validation with byte-/record-bounded DB batches and cleanup, provider secret
  handling, provider instance identity, local Ollama endpoint
  allow-listing, explicit per-indexing OpenAI cloud confirmation, Unicode-safe 1 KiB embedding
  chunks with byte-weighted normalized pooling, embedding validation,
  confirmed-batch run progress, five-minute Ollama batch keep-alive, visible-view
  non-overlapping two-second run polling, bounded parallel indexing/cluster-set
  starts within local worker/resource limits, bounded clustering, curation preservation,
  cluster-set job progress/cancellation, OpenAI confirmation for LLM summaries,
  LLM prompt/response bounds, redacted provider diagnostics, project-scoped
  source dialogs and Explorer exports that do not implicitly include raw source
  dialog text.

See `docs/architecture/overview.md` for the durable architecture description.

## Repository conventions

- Source directories: `backend/`, `frontend/src/`, `deployment/docker/`.
- Test directories: `tests/` for backend/service/API/migration tests; `frontend/src/*.test.tsx` for frontend smoke/component tests.
- Naming conventions: backend domain packages mirror product capabilities; SQL migrations use zero-padded numeric prefixes.
- Error-handling conventions: new indexing and cluster-set actions use stable
  Problem Details codes without exposing secrets, raw support text, provider
  bodies or stack traces; frontend action errors preserve only sanitized
  `ApiRequestError` details or use action-specific safe fallbacks. Cluster
  `suggestedAction` fields use stable catalogued recovery codes. Typed feedback
  distinguishes error, warning, information, and success with matching live-region
  semantics.
- User-facing error policy: `.ai/policies/USER_FACING_ERROR_HANDLING.md`
- Error catalog: `docs/errors/ERROR_CATALOG.md`
- Logging and telemetry conventions: MVP uses persisted audit/import/export/run records rather than production telemetry.
- Dependency policy: manifests and lockfiles are mandatory; dependency and vulnerability gates run through `./.ai/tools/check-dependencies.sh` and `verify.sh`.
- Migration policy: migrations are committed SQL files in `backend/db/migrations/` and covered by migration tests.

## Quality commands

- Locked setup: `./.ai/tools/ci-setup.sh`
- Format check: `./.ai/tools/format.sh --check`
- Lint/static analysis: `./.ai/tools/lint.sh`
- Tests: `./.ai/tools/test.sh`
- Security checks: `./.ai/tools/security.sh`
- Build/package: `./.ai/tools/build.sh`
- Browser review evidence: `./.ai/tools/ui-quality.sh browser`
- Accessibility: `./.ai/tools/ui-quality.sh accessibility`
- Visual regression: `./.ai/tools/ui-quality.sh visual-regression`
- Full verification: `./.ai/tools/verify.sh`
- User-facing error gate: `./.ai/tools/check-user-facing-errors.py`
- Orchestration state gate: `./.ai/tools/check-orchestration-state.py`
- Orchestrator CLI: `python .ai/tools/orchestrate.py`

## Constraints and known risks

- Legal or compliance constraints: Imported support text can contain personal or sensitive data; original-text exports require explicit warnings.
- Security and privacy constraints: Absolute production-access prohibition; passwords are hashes only; OpenAI keys are encrypted and write-only after save; provider/model selection is explicit.
- Compatibility constraints: MVP runtime is local Docker Compose and CI-defined toolchain only.
- Performance constraints: Provider embedding inputs are produced incrementally as
  Unicode-safe chunks of at most 1,024 UTF-8 bytes, retaining at most the current
  batch of 64; responses, vector dimensions, and
  clustering record counts are bounded; imports stream through a two-slot 512 MiB
  wire/temp bound, use 4 MiB/1,000-record DB batches, and retain at most 100 skipped
  details; two fixed indexing workers use an
  eight-entry queue, clustering preflights a conservative 5 GiB working-set
  budget before native pgvector loading, applying that budget per parent group for
  per-parent refinement, including the preallocated float32 matrix, estimator
  matrices, bounded fetch/nearest-neighbor workspaces, linkage-specific
  graph/intermediate structures, results/mappings, and per-record overhead;
  Agglomerative rejects disconnected neighbor graphs before estimator execution.
- Operational constraints: No production deployment; local volumes own persistence.
- Known technical debt relevant to current work: Clustering quality still depends
  on the configured embedding model and clustering parameters; semantic Explorer
  search remains future scope.

## High-value references

- Requirements location: `docs/requirements/support-knowledge-miner-mvp1.md`
- API Specification: `docs/specifications/support-knowledge-miner-mvp1.md`
- Architecture decisions: `docs/architecture/decisions/`
- Threat model:
- Security reporting: `SECURITY.md`
- Runbooks:
- UI design system: `docs/design/DESIGN_SYSTEM.md`
- UI component catalog: `docs/design/COMPONENT_CATALOG.md`
- User-facing error catalog: `docs/errors/ERROR_CATALOG.md`
## Bootstrap configuration

- Project name: `Support Knowledge Miner`
- Enabled stacks: `python, react, bash`
- Python runtime: `3.13`
- Node.js runtime: `>=26.4.0,<27.0.0`
- UI quality workflow: enabled
- Repository-native orchestration: enabled
- User-facing error handling: enabled; frontend checks enabled
- Configuration source: `.ai/project.yaml`
