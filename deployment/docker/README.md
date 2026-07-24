# Local Docker Runtime

This directory contains local-only Docker Compose assets for Support Knowledge Miner.
Do not point these services at production data, production credentials, or production networks.

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

## vLLM Local Model Path

The MVP local model provider path is represented as optional Compose profiles so normal database tests do not download or start model images.
GPU is the default local model path when the host has the NVIDIA container runtime:

```bash
docker compose --env-file deployment/docker/.env.example -f deployment/docker/compose.yml --profile vllm-gpu up -d vllm-gpu
```

CPU fallback is available for hosts without GPU support or for constrained local testing:

```bash
docker compose --env-file deployment/docker/.env.example -f deployment/docker/compose.yml --profile vllm-cpu up -d vllm-cpu
```

Both profiles expose an OpenAI-compatible local endpoint at `http://localhost:8000/v1` by default and share the persistent `vllm-cache` volume for model artifacts. The endpoint can also be supplied by a separately managed local vLLM process through `SKM_VLLM_BASE_URL`; later provider/profile work should consume that setting rather than hard-coding a service name.

`VLLM_IMAGE`, `VLLM_MODEL`, and `VLLM_PORT` are local runtime knobs. Do not use production credentials, production datasets, or production networks with these services.

## Ollama Local Model Path

Ollama is available as an optional local runtime for demand-loaded local models:

```bash
docker compose --env-file deployment/docker/.env.example -f deployment/docker/compose.yml --profile ollama up -d ollama
```

Pull the local models you want to make available before selecting them in an analysis profile:

```bash
docker compose --env-file deployment/docker/.env.example -f deployment/docker/compose.yml exec ollama ollama pull nomic-embed-text
```

The provider UI can also download and add one named model through the local Ollama API. This uses the configured Ollama endpoint and is restricted by the backend to local Ollama hosts.

The default endpoint is `http://localhost:11434`. `SKM_OLLAMA_MODELS` is a comma-separated default allow-list that the backend seeds into the Ollama provider only when no Ollama provider configuration exists yet. Users can later refresh installed models or download and add one named model in the provider UI.

`OLLAMA_KEEP_ALIVE=0` unloads models after requests; use a duration such as `5m` to keep recently used models warm between analysis batches.
