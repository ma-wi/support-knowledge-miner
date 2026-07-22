# Local Docker Runtime

This directory contains local-only Docker Compose assets for Support Knowledge Miner.
Do not point these services at production data, production credentials, or production networks.

## PostgreSQL with pgvector

Start the local database:

```bash
docker compose --env-file deployment/docker/.env.example -f deployment/docker/compose.yml up -d postgres
```

The `postgres-data` named volume persists database state across container restarts.
For local development, set `SKM_DATABASE_URL` to the matching PostgreSQL URL, for example:

```bash
export SKM_DATABASE_URL=postgresql://support_knowledge_miner:replace-with-local-dev-password@localhost:5432/support_knowledge_miner
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
