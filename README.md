# Support Knowledge Miner

Support Knowledge Miner is a local-first MVP for extracting, curating, and exporting reusable support knowledge from historical paired support records. It is intended for an analyst/curator who imports CSV or JSON message-answer pairs, configures local or cloud model profiles, reviews clusters and candidates, and exports traceable CSV outputs.

The MVP is explicitly local-only. Do not connect it to production systems, production data, production credentials, or production networks.

## Implemented MVP Workflows

- Sign in with a seeded local user's email and manage equal-permission users.
- Create, open, rename, and delete independent projects.
- Import CSV or JSON records with `ticketid`, `messagegroupid`, `message`, and `answer` fields.
- Persist dataset versions, import logs, skipped-record reasons, and audit actor identity.
- Configure global OpenAI, Ollama, and vLLM providers; OpenAI API keys are write-only after save.
- Create project analysis profiles with explicit provider/model selection.
- Start local analysis-run scaffolds with observable status, progress, run metadata, embeddings, and diagnostics.
- Generate deterministic non-quadratic clustering scaffolds with outlier/source traceability.
- Curate clusters and candidates while preserving automatic, manual, and effective values separately.
- Export candidate CSV and source-assignment CSV files with persisted export metadata and original-text warnings.
- Use the React sidebar shell to reach sign-in, settings, project, import, profile, run, cluster, candidate, and export workflows.

The durable product behavior is specified in `docs/specifications/support-knowledge-miner-mvp1.md`.

## Technology

- Backend: Python 3.13, FastAPI, psycopg, PostgreSQL with pgvector.
- Frontend: React 19, TypeScript, Vite, Vitest, Testing Library, Oxlint, Prettier.
- Runtime: local Docker Compose PostgreSQL/pgvector; optional Ollama and vLLM GPU or CPU profiles.
- Security-sensitive libraries: Argon2id via `argon2-cffi` for passwords and `cryptography` for provider secret encryption.

## Setup

Install dependencies with the repository setup gate:

```bash
./.ai/tools/ci-setup.sh
```

Start the local database when exercising the backend against PostgreSQL:

```bash
docker compose --env-file deployment/docker/.env.example -f deployment/docker/compose.yml up -d postgres
```

The backend uses `SKM_DATABASE_URL` when set. Otherwise, it derives a local
PostgreSQL URL from `POSTGRES_*` values in the process environment or
`deployment/docker/.env` / `.env.example`, matching the Compose database settings.
Set `SKM_DATABASE_URL` only when you need an explicit override:

```bash
export SKM_DATABASE_URL=postgresql://support_knowledge_miner:replace-with-local-dev-password@localhost:5432/support_knowledge_miner
```

Before saving OpenAI keys locally, provide a provider encryption key outside source control:

```bash
export SKM_PROVIDER_ENCRYPTION_KEY="$(uv run --locked python -c 'from backend.providers.secrets import generate_provider_secret_key; print(generate_provider_secret_key())')"
```

Before the first backend start on an empty database, configure the initial local
user. There are no built-in default login credentials:

```bash
export SKM_INITIAL_PASSWORD='replace-with-local-password'
export SKM_INITIAL_EMAIL=owner@example.test
export SKM_INITIAL_FIRST_NAME=Local
export SKM_INITIAL_LAST_NAME=Owner
```

The initial user is created only when the user table is empty. After that, signed-in
users manage further local users in the application. Email is the only stored login
identity and the only public request/response identity field.

See `deployment/docker/README.md` for PostgreSQL and optional Ollama/vLLM runtime details.

## Run

Run the backend locally:

```bash
uv run --locked python -m backend.main
```

The command starts a Uvicorn server on `http://127.0.0.1:8080` and keeps running
until stopped with `Ctrl+C`. On startup it applies local database migrations and
then creates the initial user if the user table is empty and `SKM_INITIAL_*` is
configured. In another terminal, verify it with:

```bash
curl http://127.0.0.1:8080/api/health
```

If the command exits during startup, read the Uvicorn traceback in the terminal.
Database password authentication errors usually mean the existing local PostgreSQL
volume was initialized with different `POSTGRES_*` credentials than the current
`.env`; see `deployment/docker/README.md` before deleting any local data.

Run the frontend locally:

```bash
cd frontend
npm run dev
```

The Vite dev server proxies `/api/*` requests to the backend at
`http://127.0.0.1:8080` by default. Start the backend before signing in through
the frontend.

For local model serving, use the optional Ollama or vLLM Compose profiles documented in `deployment/docker/README.md`.
Ollama configuration is restricted to the reviewed local hosts `localhost`,
`127.0.0.1`, `::1`, and the Compose service name `ollama`.

## Verification

Run the full required gate:

```bash
./.ai/tools/verify.sh
```

Focused gates are also available:

```bash
./.ai/tools/format.sh --check
./.ai/tools/lint.sh
./.ai/tools/test.sh
./.ai/tools/check-dependencies.sh
./.ai/tools/security.sh
./.ai/tools/build.sh
python .ai/tools/check-docs.py
```

To execute fresh and stopped-at-0009 migrations against an isolated local
PostgreSQL container:

```bash
./deployment/docker/scripts/smoke-migrations.sh
```

## Configuration

- `SKM_DATABASE_URL`: optional explicit local PostgreSQL URL. When unset, the backend derives the URL from local `POSTGRES_*` settings. The backend rejects non-local database hosts.
- `SKM_PROVIDER_ENCRYPTION_KEY`: required before saving OpenAI provider API keys.
- `SKM_INITIAL_PASSWORD`, `SKM_INITIAL_EMAIL`: required together to seed the first local user on an empty database. The email address is the login name.
- `SKM_INITIAL_FIRST_NAME`, `SKM_INITIAL_LAST_NAME`: optional initial-user display names.
- `SKM_VLLM_BASE_URL`: optional local vLLM-compatible endpoint.
- `SKM_OLLAMA_BASE_URL`, `SKM_OLLAMA_MODELS`: optional local Ollama endpoint and comma-separated default model allow-list. The backend seeds this provider only when no Ollama provider is configured yet.
- `POSTGRES_*`, `VLLM_*`, `OLLAMA_*`: local Docker Compose settings in `deployment/docker/.env.example`.

Do not commit secrets or local `.env` files.

## Architecture

See `docs/architecture/overview.md` and the ADRs in `docs/architecture/decisions/`.

## Security

See `SECURITY.md`.
