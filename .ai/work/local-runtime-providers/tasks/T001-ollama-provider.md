# T001 ollama provider

- Status: verified

## Scope

Added Ollama as a local provider across persistence constraints, provider checks, frontend configuration, optional local Compose runtime, and documentation. Startup can seed an Ollama provider from `SKM_OLLAMA_BASE_URL` and `SKM_OLLAMA_MODELS` only when no Ollama provider exists yet. The provider UI can refresh installed Ollama models and can download one named model through the local Ollama `/api/pull` endpoint, then add it to the configured allow-list after success. The manual Ollama model-list input is intentionally not shown in the UI; the list is managed by refresh and pull actions. The analysis execution implementation remains the existing deterministic scaffold and records selected provider/model metadata.

## Verification

- `uv run --locked ruff format --check backend tests`: PASS
- `uv run --locked ruff check backend tests`: PASS
- `uv run --locked mypy backend tests`: PASS
- `uv run --locked python -m pytest tests/providers/test_provider_model_discovery.py tests/api/test_provider_profile_api_integration.py`: PASS, 10 tests
- `cd frontend && npm run format:check`: PASS
- `cd frontend && npm run lint`: PASS
- `cd frontend && npm run typecheck`: PASS
- `cd frontend && npm run test`: PASS, 11 tests
- `cd frontend && npm run build`: PASS
