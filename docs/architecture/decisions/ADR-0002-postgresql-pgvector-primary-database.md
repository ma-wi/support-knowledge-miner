# ADR-0002: PostgreSQL with pgvector as primary database

- Status: accepted
- Date: 2026-07-19
- Owners: User
- Related requirement: support-knowledge-miner-mvp1
- External reference identifiers: none

## Context

The MVP must persist projects, imported source text, dataset versions, analysis profiles, analysis runs, embeddings, clusters, curation state, candidates, audit/import/export metadata, and traceability links. The draft Lastenheft mentioned MongoDB, but discovery identified a stronger need for relational consistency, joins, migrations, project isolation, and vector search.

## Decision

Use PostgreSQL with pgvector as the primary local database. PostgreSQL is provided by Docker Compose with a persistent volume. Store structured project data, source text, embeddings, and vector-search state in PostgreSQL/pgvector where practical. Use project-scoped persistent filesystem/Docker volumes only for bulky non-query artifacts such as model caches, generated export files, or large batch artifacts.

## Alternatives considered

- MongoDB as primary database: rejected because the domain requires strong relational traceability and constraints.
- MongoDB plus separate vector database: rejected for MVP because it adds operational complexity and consistency boundaries.
- Separate dedicated vector database: deferred until concrete performance needs exceed pgvector.

## Consequences

### Positive

- One durable database for relational state and vector search.
- Stronger constraints and migrations.
- Simpler Docker Compose topology than database plus separate vector store.
- Better fit for candidate/source/run traceability.

### Negative

- Less schema-flexible than document storage.
- Requires schema/migration discipline.
- Very large vector indexes may require tuning or future split-out.

### Risks and mitigations

- Risk: pgvector performance may be insufficient for future scale or advanced ANN needs.
- Mitigation: keep vector/index access behind repository/service boundaries so a future vector store can be introduced if measured need appears.

## Validation

- Migration/schema tests confirm pgvector availability.
- Persistence tests verify source text, embeddings, runs, clusters, candidates, and exports survive container restart.
- Performance design/tests verify clustering does not require full pairwise all-record distance computation.
