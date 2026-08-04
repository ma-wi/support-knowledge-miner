# Specification: Local runtime and model providers

- Requirement ID: local-runtime-providers
- Status: ready-for-implementation
- Ready for implementation: yes
- Requirement source: user request on 2026-07-23
- Accepted incremental requirements:
  `docs/requirements/chg-002-analysis-clustering-feedback.md`,
  `docs/requirements/chg-004-analyst-clustering-redesign.md`
- Decision owner: anfordernder Product Owner
- Last reviewed: 2026-08-04

## Purpose

Support Knowledge Miner separates provider configuration by model purpose:

- Embedding providers generate vectors for Indizierungen.
- LLM providers generate cluster summaries for Cluster-Sets.

OpenAI is the supported cloud provider. Ollama and vLLM are supported local
embedding providers. Ollama is also a supported local LLM provider. Provider/model
selection is always explicit at the action that uses it.

## Scope

### In scope

- Global Embedding-Provider configuration for OpenAI, Ollama and vLLM.
- Global LLM-Provider configuration for OpenAI and Ollama.
- Optional Docker Compose Ollama runtime with persistent model storage.
- Local endpoint validation before persistence and before discovery/pull/use.
- Model discovery or manual model allow-lists per provider purpose.
- Ollama model pull/download from the local provider UI.
- Five-minute Ollama embedding keep-alive.
- OpenAI secret write-only behavior.
- Explicit OpenAI confirmation before original support text is sent.

### Out of scope

- Production deployment or production access.
- Automatically pulling models from remote registries during analysis.
- Unbounded model residency after analysis activity stops.
- Multi-model orchestration for vLLM containers.
- Treating embedding models and LLM/chat models as interchangeable.

## Provider purposes

### Embedding-Provider

Supported providers:

- OpenAI Cloud.
- Ollama local.
- vLLM-compatible local endpoint.

Embedding providers are selected when starting an Indizierung. The selected model is
stored in indexing provenance and every generated embedding row.

### LLM-Provider

Supported providers:

- OpenAI Cloud.
- Ollama local.

LLM providers are selected when creating or refining a Cluster-Set. The selected
model, prompt/configuration, sample strategy, sample count, seed and output
validation result are stored in cluster-set provenance.

## Local Ollama behavior

- `SKM_OLLAMA_BASE_URL` defines the default local Ollama endpoint.
- `SKM_OLLAMA_MODELS` defines a comma-separated initial embedding allow-list.
- `SKM_OLLAMA_LLM_MODELS` may define a comma-separated initial LLM allow-list.
- Startup inserts default Ollama provider rows from these values only when no
  matching Ollama configuration exists yet.
- Existing Ollama provider configuration is never overwritten by startup seeding.
- Provider check for Ollama calls `/api/tags`, extracts local model names, and
  returns them to the UI for the selected provider purpose.
- Ollama model download calls `/api/pull` with `stream:false`, requires a local
  endpoint, and adds the requested model to the selected purpose allow-list only
  after Ollama reports success.
- Every Ollama embedding request sets `keep_alive` to `5m`.
- LLM generation requests may use bounded keep-alive behavior but must stay
  provider-purpose scoped and bounded by timeout, request size and response size.

## Endpoint and network rules

Ollama and vLLM configuration, checks, pulls and provider calls accept only:

- `localhost`
- `127.0.0.1`
- `::1`
- reviewed local Docker Compose service names used by this project

Credentials in endpoint URLs are rejected. HTTP redirects are not followed.
Non-local hostnames are rejected before any connection attempt.

OpenAI uses the fixed official cloud API host through the configured client. The
application must not silently fall back from a local provider to OpenAI or from one
model to another.

## Secret handling

OpenAI API keys and future provider secrets are write-only after storage. Normal
read APIs may return presence/status metadata but never plaintext secret values.
Provider checks and errors must not expose keys, authorization headers, raw request
payloads, raw provider bodies, internal paths or stack traces.

## UI behavior

Settings has separate tabs:

- „Embedding-Provider“
- „LLM-Provider“
- „Benutzer“

Each provider tab shows only models valid for that purpose. Empty model lists block
the action that needs a model and show a safe actionable message. Connection/model
list failures are visible and retryable.

OpenAI cloud use is confirmed at the concrete data-sending action:

- Indizierung start for embeddings.
- Cluster-Set creation/refinement when LLM summary generation sends original
  support texts.

## Error and recovery behavior

Provider-related failures use stable catalogued codes through the owning feature
action. Missing models, unavailable local services, rejected non-local endpoints,
timeouts and OpenAI confirmation failures must show safe actionable messages at the
provider settings form, Indizierung form or Cluster-Set form. Diagnostics must not
include secrets, credentials, raw support text, raw provider bodies, stack traces,
internal paths or unredacted hosts outside the configured local endpoint display.

Failed provider checks preserve configured values and offer retry. Failed
Indizierung or LLM-summary calls preserve selected model/parameters and cannot
display success.

## Acceptance criteria

- [x] AC-1: Fresh and migrated databases represent provider purpose separately for
  embedding and LLM use.
- [x] AC-2: The provider API accepts, lists, checks and updates Embedding-Provider
  and LLM-Provider configurations separately.
- [x] AC-3: OpenAI secrets are stored/replaced/removed without plaintext exposure in
  read APIs or UI.
- [x] AC-4: Ollama/vLLM endpoints reject non-local hosts, URL credentials and
  redirects before use.
- [x] AC-5: The frontend can configure and check embedding providers separately
  from LLM providers.
- [x] AC-6: The frontend can request a named Ollama model download and add it to the
  selected purpose allow-list after success.
- [x] AC-7: Indizierungen can select only configured embedding models.
- [x] AC-8: Cluster-Sets can select only configured LLM models for summaries.
- [x] AC-9: Every Ollama embedding request uses `keep_alive: "5m"` without changing
  OpenAI/vLLM payloads.
- [x] AC-10: Provider tests cover discovery, rejected endpoints, pull behavior, env
  seeding, API contract and frontend behavior for both provider purposes.
