# T003 provider model discovery and status cleanup

- Status: verified

## Scope

Removed visible task identifiers from the frontend shell, removed the redundant OpenAI API-key explanatory copy, and made transient status messages auto-clear after user actions. Updated the OpenAI provider flow so models are discovered from the configured OpenAI account and exposed as selectable analysis models. Discovery prefers embedding models when available and falls back to all returned models when no embedding-specific identifiers are present.
The explicit OpenAI model refresh action also works for already stored API keys and persists the refreshed model selection without requiring the key to be entered again.
OpenAI model parsing accepts the standard `data[].id` response plus common alternative model-list shapes and reports an explicit failure when a successful HTTP response contains no usable model identifiers.

## Verification

- `cd frontend && npm run format:check`: PASS
- `cd frontend && npm run lint`: PASS
- `cd frontend && npm run typecheck`: PASS
- `cd frontend && npm run test`: PASS, 10 tests
- `cd frontend && npm run build`: PASS
- `uv run --locked ruff format --check backend tests`: PASS
- `uv run --locked ruff check backend tests`: PASS
- `uv run --locked mypy backend tests`: PASS
- `uv run --locked python -m pytest tests/providers/test_provider_model_discovery.py tests/api/test_provider_profile_api_integration.py`: PASS, 5 tests
- `uv run --locked python -m pytest`: PASS, 78 tests
