# T001 config env fallback

- Status: verified

## Scope

Implemented and tested local PostgreSQL URL derivation from Compose-style `POSTGRES_*` environment variables and local Docker env files when `SKM_DATABASE_URL` is absent. Also made `python -m backend.main` start a local Uvicorn server, load the local env file before app startup, run local database migrations before initial-user seeding, and configured the Vite dev server to proxy `/api/*` to the local backend.

## Dependency review

- Added `uvicorn>=0.38,<1` as the ASGI server required to run the FastAPI app from the documented backend start command.
- Built-in functionality is insufficient because FastAPI exposes an ASGI application but does not run an HTTP server by itself.
- Version is constrained below the next major release and locked in `uv.lock`.

## Verification

- `uv run --locked ruff format --check backend tests`: PASS
- `uv run --locked ruff check backend tests`: PASS
- `uv run --locked mypy backend tests`: PASS
- `uv run --locked python -m pytest`: PASS, 74 tests
- `cd frontend && npm run format:check`: PASS
- `cd frontend && npm run typecheck`: PASS
- `cd frontend && npm run test`: PASS, 9 tests
- `./.ai/tools/check-dependencies.sh`: PASS
- `python .ai/tools/check-docs.py`: PASS
- `git diff --check`: PASS

## Manual startup observation

- `timeout 6s uv run --locked python -m backend.main`: PASS for startup; Uvicorn logged `Application startup complete` and `Uvicorn running on http://127.0.0.1:8080` before the timeout stopped it.
- Temporary Vite dev server on port 5175 returned `{"status":"ok"}` for `/api/health`, confirming the `/api` proxy to the backend.
