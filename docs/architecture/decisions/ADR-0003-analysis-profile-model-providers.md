# ADR-0003: Global provider configuration with analysis-profile model selection

- Status: superseded by ADR-0007
- Date: 2026-07-19
- Owners: User
- Related requirement: support-knowledge-miner-mvp1
- External reference identifiers: none

## Supersession

ADR-0007 supersedes this decision on 2026-08-04. Analysis profiles are no longer an
active product concept. Provider configuration remains global, but model and
runtime choices move to the action that uses them:

- Embedding model selection belongs to an Indizierung.
- Cluster algorithm, vector basis and optional LLM model selection belong to a
  Cluster-Set.
- LLM providers are configured separately from embedding providers.

## Context

Users need to test different embedding and language models, thresholds, prompts, and algorithms. The MVP must support OpenAI cloud models and local Ollama/vLLM providers. Provider connection settings such as OpenAI API keys and vLLM endpoints are shared application configuration, while model and analysis settings vary per project analysis profile.

## Decision

Store provider connection and credential configuration globally. Store model selection and analysis parameters per `AnalysisProfile` within a project. A project may contain multiple analysis profiles. Each analysis run references a profile snapshot so past runs remain reproducible. OpenAI is the first cloud provider. Ollama and vLLM are supported local providers. Provider/model selection must be explicit and configured through the UI; the system must not silently switch providers.

OpenAI API keys must not be returned in plaintext-readable form after storage. Ollama/vLLM endpoint settings and model discovery/manual model configuration must support multiple exposed local models that profiles can select.

## Alternatives considered

- Analysis-profile scoped provider credentials/endpoints: rejected because API keys and local-provider connection settings should be configured once and reused.
- Project-level provider setting only: rejected because one project may compare multiple model/profile combinations.

## Consequences

### Positive

- Supports repeatable model experiments while avoiding repeated credential/endpoint setup.
- Keeps run provenance clear.
- Reduces accidental cloud use by requiring explicit profile selection.

### Negative

- Requires both global provider settings UI and profile model-selection UI.
- Secret handling must be designed before implementation.

### Risks and mitigations

- Risk: accidental cloud submission of sensitive text.
- Mitigation: provider is explicit per profile; UI must show cloud provider use before running analysis.

- Risk: API key exposure.
- Mitigation: write-only read behavior for secrets and tests verifying no plaintext return through normal read APIs.

## Validation

- Tests create global provider settings, then create multiple profiles in one project and verify runs reference the selected profile snapshot.
- Secret tests verify stored OpenAI keys cannot be read back in plaintext.
- Provider adapter tests use stubs rather than mandatory live OpenAI calls.
