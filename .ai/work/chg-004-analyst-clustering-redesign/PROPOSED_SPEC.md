# Proposed target specification: Analystenorientierte Indizierungs- und Clusteranalyse

- Requirement ID: CHG-004
- Status: canonicalized
- Ready for implementation: yes
- Canonical specifications:
  - `docs/specifications/support-knowledge-miner-mvp1.md`
  - `docs/specifications/local-runtime-providers.md`
- Replacement ADR:
  `docs/architecture/decisions/ADR-0007-indexing-cluster-set-provider-split.md`
- Superseded ADR:
  `docs/architecture/decisions/ADR-0003-analysis-profile-model-providers.md`
- Last updated: 2026-08-04

## Canonicalization result

The accepted CHG-004 target behavior is now represented in the durable capability
specifications and ADR listed above. This temporary file intentionally no longer
duplicates the detailed product behavior.

## Implementation-ready decisions carried forward

- Analysis profiles are removed without compatibility.
- Runs become Indizierungen.
- Indizierungen create both `message` and `answer` embeddings.
- Cluster-Sets are persisted final analysis artifacts.
- Cluster-Sets support parent/child lineage and source snapshots.
- LLM providers are configured separately from embedding providers.
- LLM example count defaults to `10`.
- The Explorer owns filtered CSV/JSON export through a separate Export section.
- The Project tabs Profile, Runs, Kandidaten and separate Export are removed.
- The approved clickable mockup remains the design direction and must not be
  imported into production code.

## Remaining implementation detail

Exact route names, SQL table names, component boundaries, source-dialog pagination
strategy and LLM prompt wording remain implementation choices constrained by the
canonical specifications.
