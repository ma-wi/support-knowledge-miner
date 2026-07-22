# Project context

Keep this document compact. It is a map for agents, not a duplicate of the source code or README.

## Purpose

- Product or service: Local-first Support Knowledge Miner for extracting and curating FAQ/support knowledge from historical paired support messages.
- Primary users: Analyst/Kurator, a fachlich-technischer user who imports data, configures analysis profiles, reviews clusters, curates candidates, and exports results.
- Main outcome: Independent projects persist imported CSV/JSON support pairs, analysis runs, embeddings, curation state, candidates, and exports with source traceability.
- Explicit non-goals: No production access, no operational FAQ agent, no customer communication, no live ticket/shop/ERP integrations, and no server deployment in MVP 1.

## Technology stack

- Languages:
- Frameworks:
- Build system:
- Package managers:
- Runtime and supported versions:
- Deployment environment:
- Data stores:
- External services:

## Architecture map

- Entry points:
- Core modules:
- Data flow:
- Trust boundaries:
- Public interfaces:
- Generated-code locations:
- Critical paths:

See `docs/architecture/overview.md` for the durable architecture description.

## Repository conventions

- Source directories:
- Test directories:
- Naming conventions:
- Error-handling conventions:
- Logging and telemetry conventions:
- Dependency policy:
- Migration policy:

## Quality commands

- Locked setup: `./.ai/tools/ci-setup.sh`
- Format check: `./.ai/tools/format.sh --check`
- Lint/static analysis: `./.ai/tools/lint.sh`
- Tests: `./.ai/tools/test.sh`
- Security checks: `./.ai/tools/security.sh`
- Build/package: `./.ai/tools/build.sh`
- Full verification: `./.ai/tools/verify.sh`

## Engineering standards MCP

- Optional server: `engineering-knowledge`
- Availability is controlled by `.ai/project.yaml`.
- Discover its configured search/read tools when enabled; retrieve only targeted guidance.
- Record source identifiers only when guidance materially affects a decision.

## Constraints and known risks

- Legal or compliance constraints:
- Security and privacy constraints:
- Compatibility constraints:
- Performance constraints:
- Operational constraints:
- Known technical debt relevant to current work:

## High-value references

- Requirements location:
- API specification:
- Architecture decisions:
- Threat model:
- Runbooks:
## Bootstrap configuration

- Project name: `Support Knowledge Miner`
- Enabled stacks: `python, react, bash`
- Engineering knowledge MCP: `engineering-knowledge` (enabled)
- Configuration source: `.ai/project.yaml`
