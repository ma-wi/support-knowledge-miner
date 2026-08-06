# Local Docker Runtime

This directory contains local-only Docker Compose assets for Support Knowledge Miner.
Do not point these services at production data, production credentials, or production networks.

## Import Temporary Storage

Imports through 512 MiB are spooled to a permission-restricted file in the backend
host/container's standard temporary directory and parsed twice from that file. Keep
slightly more than 512 MiB of temporary disk headroom per concurrent import, in
addition to PostgreSQL space. One backend process admits at most two active imports,
so reserve slightly more than 1 GiB when both slots may receive maximum-size files.
Further attempts receive HTTP 503; uploads idle between chunks for 30 seconds or
running longer than 30 minutes are aborted. The backend deletes the file after success, validation
failure, disconnect, oversize detection, or database failure. Temporary storage is
not a persistence or recovery mechanism and must not be populated with production
data.

## PostgreSQL with pgvector

Start the local database:

```bash
docker compose --env-file deployment/docker/.env.example -f deployment/docker/compose.yml up -d postgres
```

The `postgres-data` named volume persists database state across container restarts.
`deployment/docker/.env.example` supplies the `POSTGRES_*` values used by the
PostgreSQL container. For host-run backend processes, the backend derives
`SKM_DATABASE_URL` from `POSTGRES_*` values in the process environment or from
`deployment/docker/.env` / `.env.example` when `SKM_DATABASE_URL` is not set.

PostgreSQL applies `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` only
when the data volume is initialized. Changing those values later does not update
credentials inside an existing `postgres-data` volume. If local startup fails with
database password authentication errors after changing `.env`, either restore the
old local credentials or recreate the local database volume:

```bash
docker compose --env-file deployment/docker/.env -f deployment/docker/compose.yml down -v
docker compose --env-file deployment/docker/.env -f deployment/docker/compose.yml up -d postgres
```

This deletes the local PostgreSQL data volume.

Set `SKM_DATABASE_URL` only when you need an explicit override:

```bash
export SKM_DATABASE_URL=postgresql://support_knowledge_miner:replace-with-local-dev-password@localhost:5432/support_knowledge_miner
```

If a backend container is added later, its Compose service should receive
`SKM_DATABASE_URL` directly, usually with host `postgres` and port `5432` inside the
Compose network.

Before saving OpenAI provider API keys, generate and export a local provider credential encryption key. Keep the value outside source control and rotate it only with a plan to re-enter saved provider keys:

```bash
export SKM_PROVIDER_ENCRYPTION_KEY="$(uv run --locked python -c 'from backend.providers.secrets import generate_provider_secret_key; print(generate_provider_secret_key())')"
```

Run the T001 PostgreSQL smoke test from the repository root:

```bash
deployment/docker/scripts/smoke-postgres.sh
```

The smoke test starts an isolated local Compose project, applies migrations to an empty database, verifies pgvector through the backend health query, restarts PostgreSQL, verifies database state persisted across restart, and removes its test containers, network, and volume.

Run the migration compatibility smoke test from the repository root:

```bash
./deployment/docker/scripts/smoke-migrations.sh
```

It starts a separate isolated local Compose project, executes both a fresh database
and existing databases stopped at older supported migration levels, checks provider
and identity constraints, and removes all test resources.

Before applying migrations to a local development database that contains work you
need to keep, take a local backup of the `postgres-data` volume or export the data
you need. Migration `0014_indexing_runs_without_profiles.sql` is intentionally
destructive for obsolete local derived analysis data: it removes analysis profiles
and resets profile-derived runs, embeddings, clusters, obsolete candidate-derived
data and exports while
preserving projects, imports, dataset versions and provider configuration. Do not
run these local migration procedures against production data, production
credentials, production networks or any production-controlled resource.

## Ollama Local Model Path

Ollama is available as an optional local runtime for demand-loaded local models:

```bash
docker compose --env-file deployment/docker/.env.example -f deployment/docker/compose.yml --profile ollama up -d ollama
```

Pull the local models you want to make available before selecting them for an
indexing or clustering action:

```bash
docker compose --env-file deployment/docker/.env.example -f deployment/docker/compose.yml exec ollama ollama pull nomic-embed-text
```

The provider UI can also download and add one named model through the local Ollama
API. Saving, model discovery, and model download are restricted before network access
to `localhost`, `127.0.0.1`, `::1`, or the Compose service name `ollama`. The backend
does not follow redirects.

The default endpoint is `http://localhost:11434`. `SKM_OLLAMA_MODELS` is a comma-separated default allow-list that the backend seeds into the Ollama provider only when no Ollama provider configuration exists yet. Users can later refresh installed models or download and add one named model in the provider UI.

`OLLAMA_KEEP_ALIVE=5m` keeps the selected model warm between normal indexing
batches and allows Ollama to unload it again after five minutes without activity.

## Deferred runtimes

vLLM is not exposed as an active local runtime in this MVP. It can be added later
through a new reviewed provider/runtime change.
