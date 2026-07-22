# ADR-0004: Local Docker Compose runtime with GPU default and CPU fallback

- Status: accepted
- Date: 2026-07-19
- Owners: User
- Related requirement: support-knowledge-miner-mvp1
- External reference identifiers: none

## Context

The first delivery must run locally, not on a server. The local environment has a GPU. The stack needs persistent storage and local model serving. Server deployment and production-grade operations are deferred.

## Decision

Use Docker Compose as the local MVP runtime. Compose must provide PostgreSQL/pgvector with persistent volume and a vLLM service or configurable vLLM endpoint path. Local model/analysis workloads should use GPU by default where available, with CPU fallback required for compatibility and tests.

## Alternatives considered

- Server-first deployment: rejected for MVP.
- Host-installed services without Compose: rejected because reproducibility and persistence setup would be weaker.
- CPU-only local model runtime: rejected because local GPU is available and expected; CPU fallback remains required.

## Consequences

### Positive

- Reproducible local environment.
- Persistent local data volumes.
- Enables local model execution without cloud dependency.
- Keeps future server deployment separate from MVP scope.

### Negative

- GPU Compose configuration can vary by host and driver setup.
- vLLM images/models may be large.

### Risks and mitigations

- Risk: local GPU runtime unavailable on some machines.
- Mitigation: CPU fallback path and tests that do not require GPU.

- Risk: model downloads/cache consume large disk space.
- Mitigation: model cache uses explicit persistent volume and should be documented.

## Validation

- Compose smoke test starts required services.
- Persistence test verifies database state survives restart.
- Local tests can run without GPU and without live cloud credentials.
