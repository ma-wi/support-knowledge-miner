# Specification: Local runtime providers

- Requirement ID: local-runtime-providers
- Status: ready-for-implementation
- Ready for implementation: yes
- Requirement source: user request on 2026-07-23
- Decision owner: User
- Last reviewed: 2026-07-23

## Purpose

Support Knowledge Miner supports Ollama as an additional local model provider alongside vLLM. Ollama is intended for locally available models that can be managed by Ollama and selected explicitly in analysis profiles.

## Scope

- Add `ollama` as a valid provider in provider configuration, analysis profiles, and analysis runs.
- Provide an optional Docker Compose Ollama runtime with persistent model storage.
- Seed a default Ollama provider configuration from local environment values only when no Ollama configuration exists yet.
- Allow users to configure the Ollama endpoint in the provider UI.
- Allow users to refresh the Ollama model allow-list from the local Ollama `/api/tags` endpoint.
- Allow users to download one named Ollama model from the provider UI and add it to the allow-list after a successful local pull.
- Keep Ollama analysis profiles non-cloud.
- Preserve existing OpenAI and vLLM behavior.

## Out Of Scope

- Production deployment or production access.
- Automatically pulling models from remote registries during analysis.
- Replacing the existing deterministic analysis scaffold with real provider embedding execution in this slice.
- Multi-model orchestration for vLLM containers.

## Behavior

- `SKM_OLLAMA_BASE_URL` defines the default local Ollama endpoint.
- `SKM_OLLAMA_MODELS` defines a comma-separated initial allow-list.
- Startup inserts the Ollama provider from these values only when no Ollama provider row exists.
- Existing Ollama provider configuration is never overwritten by startup seeding.
- Provider check for Ollama calls `/api/tags`, extracts local model names, and returns them to the UI.
- If Ollama is unavailable, the provider check returns the configured model allow-list with `ok=false` and a diagnostic message.
- Ollama model download calls `/api/pull` with `stream:false`, requires a local endpoint, and adds the requested model to the configured allow-list only after Ollama reports success.
- Analysis profile creation rejects Ollama models that are not in the configured Ollama model list.

## Acceptance Criteria

- Fresh and migrated databases accept `ollama` provider values.
- The provider API accepts, lists, and checks Ollama provider configuration.
- The frontend can save the Ollama endpoint and refresh local model names.
- The frontend can request a named Ollama model download and show the updated allow-list after success.
- Analysis profiles can select Ollama and are marked `is_cloud_provider=false`.
- Local Docker Compose includes an optional Ollama profile and persistent model store.
- Tests cover migration constraints, provider discovery, Ollama pull behavior, env seeding, API contract, and frontend behavior.
