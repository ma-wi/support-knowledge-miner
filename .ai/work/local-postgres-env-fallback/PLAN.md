# Plan: local runtime and frontend usability updates

- Requirement ID: local-postgres-env-fallback
- Status: verification
- Change class: normal
- Rationale: Backend configuration and frontend provider behavior changed, but scope is bounded to local runtime setup, navigation, and OpenAI model discovery.
- Requirement: user requests on 2026-07-23
- Durable specification: not required

## Acceptance criteria

- `SKM_DATABASE_URL` remains the highest-priority explicit database URL.
- When `SKM_DATABASE_URL` is absent, backend derives a local PostgreSQL URL from Compose-style `POSTGRES_*` values.
- Missing `POSTGRES_*` values keep safe local defaults.
- Non-local database targets remain rejected.
- `python -m backend.main` starts the local backend and runs migrations before initial-user seeding.
- Vite dev frontend proxies `/api/*` to the local backend.
- Signed-in frontend has separate pages for projects/analyses, providers/vLLM, and user management.
- Provider/user pages are reachable through the profile menu, including sign-out.
- Transient status messages clear automatically after actions.
- Visible task identifiers and redundant OpenAI API-key copy are removed from the frontend.
- OpenAI provider checks discover available models automatically, prefer embedding models, and fall back to all models when no embedding identifiers are available.

## Verification

- `uv run --locked ruff format --check backend tests`
- `uv run --locked ruff check backend tests`
- `uv run --locked mypy backend tests`
- `uv run --locked python -m pytest tests/providers/test_provider_model_discovery.py tests/api/test_provider_profile_api_integration.py`
- `cd frontend && npm run format:check`
- `cd frontend && npm run lint`
- `cd frontend && npm run typecheck`
- `cd frontend && npm run test`
- `cd frontend && npm run build`
- `python .ai/tools/check-docs.py`
- `git diff --check`
