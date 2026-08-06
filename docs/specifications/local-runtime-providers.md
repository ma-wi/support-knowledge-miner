# Specification: Local runtime and model providers

- Requirement ID: local-runtime-providers
- Status: ready-for-implementation
- Ready for implementation: yes
- Requirement source: user request on 2026-07-23
- Accepted incremental requirements:
  `docs/requirements/chg-002-analysis-clustering-feedback.md`,
  `docs/requirements/chg-004-analyst-clustering-redesign.md`
- Decision owner: anfordernder Product Owner
- Last reviewed: 2026-08-05

## Purpose

Support Knowledge Miner centralizes provider configuration by provider instance:

- Provider instances keep discovered/available models separate from the models
  explicitly released for Indizierung embeddings.
- Provider instances keep discovered/available models separate from the models
  explicitly released for Cluster-Set LLM summaries.

OpenAI is the supported cloud provider. Ollama is the supported local runtime
provider. vLLM is not active in the current UI/API/runtime; historical provenance
may remain readable but vLLM cannot be configured or called for new work.
Provider/model selection is always explicit at the action that uses it.
Indizierung can optionally normalize line breaks only for the embedding-provider
input: preserve line breaks, remove line breaks, or replace line-break groups with
a bounded user-provided replacement string. It can also lowercase provider input
after line-break normalization. Imported source texts remain unchanged; active
normalization is stored in indexing parameters and embedding metadata.

## Scope

### In scope

- Global Provider configuration for multiple OpenAI and Ollama instances.
- Separate discovered/available models plus embedding and LLM model allow-lists per
  provider instance.
- Optional Docker Compose Ollama runtime with persistent model storage.
- Local endpoint validation before persistence and before discovery/pull/use.
- Model discovery or manual model allow-lists per provider instance and purpose.
- Ollama model pull/download from the selected local provider UI.
- Five-minute Ollama embedding keep-alive.
- OpenAI secret write-only behavior.
- Explicit OpenAI confirmation before original support text is sent.

### Out of scope

- Production deployment or production access.
- Automatically pulling models from remote registries during analysis.
- Unbounded model residency after analysis activity stops.
- vLLM configuration, orchestration or runtime calls.
- Treating embedding models and LLM/chat models as interchangeable.

## Provider instances and purposes

Supported provider base types:

- OpenAI Cloud.
- Ollama local.

Each provider instance has a stable technical ID and editable display name. Display
names are user-controlled and may be duplicated; the technical ID is the identity.
Instances can be added and hard-deleted from active configuration. Historical
indexing and cluster-set records snapshot provider name, base type and model so
logs remain understandable after deletion.

Provider purpose is derived from allow-lists, not from separate purpose flags. A
provider can be selected for Indizierung only when its embedding-model allow-list is
non-empty. The selected provider instance, provider base type, display name and
model are stored in indexing provenance and every generated embedding row.

A provider can be selected for Cluster-Set summaries only when its LLM-model
allow-list is non-empty. The selected provider instance, provider base type,
display name, model, prompt/configuration, sample strategy, sample count, seed and
output validation result are stored in cluster-set provenance.

Model discovery refreshes the provider's available-model list. Models that are no
longer returned by the provider disappear from the available list and are removed
from embedding/LLM allow-lists on the next save. Unchecking a model changes only
the relevant allow-list; the model remains visible, unchecked, and in the same
available-model order until provider discovery removes it.

OpenAI model lists are purpose-filtered. Embedding options contain only
`text-embedding-*` models. LLM options contain only `gpt-n*` models with `n >= 5`
plus `o4-mini`, `gpt-4.1*` and `gpt-4o*`.

## Local Ollama behavior

- `SKM_OLLAMA_BASE_URL` defines the default local Ollama endpoint.
- `SKM_OLLAMA_MODELS` defines a comma-separated initial embedding allow-list.
- `SKM_OLLAMA_LLM_MODELS` may define a comma-separated initial LLM allow-list.
- Startup inserts a default Ollama provider instance from these values only when no
  Ollama configuration exists yet.
- Existing Ollama provider instances are never overwritten by startup seeding.
- Provider check for Ollama calls `/api/tags`, extracts local model names, and
  returns them to the selected provider instance card.
- Ollama model download calls `/api/pull` with `stream:false`, requires a local
  endpoint, and adds the requested model to the selected provider's available
  models only after Ollama reports success. The user releases it for embedding
  and/or LLM use via the model checkboxes and `Provider speichern`.
- At most one Ollama model download can run globally. The UI shows a running state
  and final success/failure status; percentage progress is not required.
- Every Ollama embedding request sets `keep_alive` to `5m`.
- LLM generation requests may use bounded keep-alive behavior but must stay
  provider-purpose scoped and bounded by timeout, request size and response size.

## Endpoint and network rules

Ollama configuration, checks, pulls and provider calls accept only:

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

Settings has only these tabs:

- „Provider“
- „Nutzer“

The Provider tab contains OpenAI/Ollama instance cards. Each card shows editable
display name, connection settings, embedding-model checkboxes, LLM-model
checkboxes, connection-test action, model-discovery action, save action and remove
action. There is no separate purpose checkbox and no separate model-release save
button; `Provider speichern` persists connection settings and model allow-lists.
Empty model allow-lists block the action that needs a model and show a safe
actionable message. Connection/model-list failures are visible and retryable.

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

- [x] AC-1: Fresh and migrated databases represent multiple provider instances
  with available models plus separate embedding and LLM allow-lists.
- [x] AC-2: The provider API accepts, lists, checks, adds, updates and deletes
  central Provider configurations by stable provider instance ID.
- [x] AC-3: OpenAI secrets are stored/replaced/removed without plaintext exposure in
  read APIs or UI.
- [x] AC-4: Ollama endpoints reject non-local hosts, URL credentials and redirects
  before use.
- [x] AC-5: The frontend can configure and check OpenAI/Ollama provider instances
  in the central Provider tab.
- [x] AC-6: The frontend can request a named Ollama model download, add it to the
  available model list after success and release it through provider save.
- [x] AC-7: Indizierungen can select only configured embedding models.
- [x] AC-8: Cluster-Sets can select only configured LLM models for summaries.
- [x] AC-9: Every Ollama embedding request uses `keep_alive: "5m"` without changing
  OpenAI payloads.
- [x] AC-10: Provider tests cover discovery, rejected endpoints, pull behavior, env
  seeding, API contract and frontend behavior for both provider purposes.
