# Plan: local runtime providers

- Requirement ID: local-runtime-providers
- Status: verification
- Change class: significant
- Rationale: Adds a new provider value that touches API contracts, database constraints, local runtime configuration, frontend behavior, and documentation.
- Requirement: user request on 2026-07-23
- Durable specification: `docs/specifications/local-runtime-providers.md`

## Acceptance criteria

- Ollama is accepted as a provider anywhere provider values are validated or persisted.
- Existing databases can migrate provider/profile/run constraints to include `ollama`.
- Fresh databases include `ollama` in provider/profile/run constraints.
- Ollama provider configuration supports endpoint URL and a manually curated model list.
- Ollama provider check discovers local models from an Ollama endpoint and falls back to the curated list on connection failure.
- Frontend provider page exposes Ollama configuration and model refresh.
- Analysis profiles can select `ollama` and mark it as non-cloud.
- Local Docker Compose documents and exposes an optional Ollama runtime profile.
- Frontend uses a left-sidebar shell with project and settings areas.
- Settings are split into Embedding-Provider and Nutzer tabs.
- Project-specific workflows are split into project tabs.
- User-facing authentication and user management use email as the login identifier, with no separate username field.

## Verification

- `uv run --locked ruff format --check backend tests`
- `uv run --locked ruff check backend tests`
- `uv run --locked mypy backend tests`
- `uv run --locked python -m pytest`
- `cd frontend && npm run format:check`
- `cd frontend && npm run lint`
- `cd frontend && npm run typecheck`
- `cd frontend && npm run test`
- `cd frontend && npm run build`
- `python .ai/tools/check-work-state.py`
- `python .ai/tools/check-docs.py`
- `git diff --check`
