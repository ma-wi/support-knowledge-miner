# ADR-0001: Project-scoped workspace isolation

- Status: accepted
- Date: 2026-07-19
- Owners: User
- Related requirement: support-knowledge-miner-mvp1
- External reference identifiers: none

## Context

Support Knowledge Miner must let users create/open saved work states. A dataset/analysis is understood as a project. Projects must be absolutely independent so that imports, analysis runs, curation, candidates, exports, model/profile choices, and artifacts can be reopened without leaking or mixing state across workspaces.

## Decision

Use `Project` as the top-level isolation and ownership boundary. All durable domain records must either directly carry `project_id` or be reachable only through a parent record with project scope. Required MVP lifecycle operations are create, open/list, rename, and delete.

Project deletion is a confirmed destructive operation that removes project-owned database state and project artifact paths after explicit confirmation.

## Alternatives considered

- Dataset as the top-level boundary: rejected because one project can contain multiple dataset versions, profiles, runs, curation states, and exports.
- Global datasets with filters: rejected because it increases leakage risk and makes reopenable project state ambiguous.

## Consequences

### Positive

- Clear user mental model.
- Stronger data isolation.
- Easier traceability from candidate/export back to source import.
- Supports multiple analysis profiles and runs per project.

### Negative

- Every query and artifact path must enforce project scope.
- Project deletion requires careful cascade behavior.

### Risks and mitigations

- Risk: cross-project data leakage through missing filters.
- Mitigation: enforce project scope in data access services and add project-isolation tests.

## Validation

- Project isolation tests create two projects and verify imports, profiles, runs, candidates, and exports are not cross-visible.
- Delete tests verify project-owned data/artifacts are removed or marked deleted according to the specification.
