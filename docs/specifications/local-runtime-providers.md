# Specification: Local runtime providers

- Requirement ID: local-runtime-providers
- Status: ready-for-implementation
- Ready for implementation: yes
- Requirement source: user request on 2026-07-23
- Accepted incremental requirement:
  `docs/requirements/chg-002-analysis-clustering-feedback.md`
- Decision owner: User
- Last reviewed: 2026-07-28

## Purpose

Support Knowledge Miner supports Ollama as an additional local model provider alongside vLLM. Ollama is intended for locally available models that can be managed by Ollama and selected explicitly in analysis profiles.

## Scope

- Add `ollama` as a valid provider in provider configuration, analysis profiles, and analysis runs.
- Provide an optional Docker Compose Ollama runtime with persistent model storage.
- Seed a default Ollama provider configuration from local environment values only when no Ollama configuration exists yet.
- Allow users to configure the Ollama endpoint in the provider UI.
- Restrict Ollama endpoints to explicitly reviewed local hostnames before persistence
  or any discovery/pull request.
- Allow users to refresh the Ollama model allow-list from the local Ollama `/api/tags` endpoint.
- Allow users to download one named Ollama model from the provider UI and add it to the allow-list after a successful local pull.
- Keep Ollama analysis profiles non-cloud.
- Preserve existing OpenAI and vLLM behavior.

## Out Of Scope

- Production deployment or production access.
- Automatically pulling models from remote registries during analysis.
- Unbounded model residency after analysis activity stops.
- Multi-model orchestration for vLLM containers.

## Behavior

- `SKM_OLLAMA_BASE_URL` defines the default local Ollama endpoint.
- `SKM_OLLAMA_MODELS` defines a comma-separated initial allow-list.
- Startup inserts the Ollama provider from these values only when no Ollama provider row exists.
- Existing Ollama provider configuration is never overwritten by startup seeding.
- Provider check for Ollama calls `/api/tags`, extracts local model names, and returns them to the UI.
- Ollama configuration, checks, and pulls accept only `localhost`, `127.0.0.1`,
  `::1`, or the local Compose service name `ollama`; credentials in the endpoint URL
  and all other hostnames are rejected before a connection. HTTP redirects are not
  followed.
- If Ollama is unavailable, the provider check returns the configured model allow-list with `ok=false` and a diagnostic message.
- Ollama model download calls `/api/pull` with `stream:false`, requires a local endpoint, and adds the requested model to the configured allow-list only after Ollama reports success.
- Analysis profile creation rejects Ollama models that are not in the configured Ollama model list.
- Every Ollama embedding request sets `keep_alive` to `5m`. The local Compose
  fallback and example use `OLLAMA_KEEP_ALIVE=5m`, keeping the selected model warm
  between normal analysis batches while allowing it to unload after inactivity.
- OpenAI and vLLM embedding payloads do not receive Ollama-specific fields.

## Acceptance Criteria

- Fresh and migrated databases accept `ollama` provider values.
- The provider API accepts, lists, and checks Ollama provider configuration.
- The frontend can save the Ollama endpoint and refresh local model names.
- The frontend can request a named Ollama model download and show the updated allow-list after success.
- Analysis profiles can select Ollama and are marked `is_cloud_provider=false`.
- Local Docker Compose includes an optional Ollama profile and persistent model store.
- Ollama embedding adapter tests verify `keep_alive: "5m"` on every batch, unchanged
  OpenAI/vLLM payloads, and a matching Compose default/example.
- Tests cover executable fresh and stopped-at-0009 migration constraints, provider
  discovery, rejected non-local endpoints before connection, Ollama pull behavior,
  env seeding, API contract, and frontend behavior.
