# Implementation plan: Support Knowledge Miner MVP 1

- Status: accepted
- Change class: significant
- Requirement: `docs/requirements/support-knowledge-miner-mvp1.md`
- Durable specification: `docs/specifications/support-knowledge-miner-mvp1.md`
- Work directory: `.ai/work/support-knowledge-miner-mvp1/`
- Last updated: 2026-07-22

## Outcome and implementation boundary

Implement the accepted MVP foundation for a local-first Support Knowledge Miner. The work must establish durable project-scoped persistence, authentication/user audit, import, provider/profile configuration, analysis-run scaffolding, curation/export foundations, and UI workflows described by the specification.

- In scope: accepted MVP behavior from the durable specification, split into reviewable milestones.
- Non-goals: production access, server deployment, live support-system integrations, operational FAQ answering, differentiated roles, Ollama support.
- Accepted assumptions relevant to implementation: PostgreSQL/pgvector primary DB; vLLM only local provider; OpenAI first cloud provider; Docker Compose local runtime; GPU default with CPU fallback; passwords are hashes only; provider credentials are write-only after save.
- Open blockers: none for first milestone planning.

## Current-state findings and approach

- Relevant existing components and test seams: repository has Python backend skeleton, React frontend skeleton, and verification scripts. Specification defines backend API/service boundary as primary test seam.
- Proposed implementation: build vertically from secure local foundation to project/import/profile/run workflows, then analysis/curation/export slices. Each task must add lowest-useful automated tests and keep behavior project-scoped.
- Alternatives rejected for implementation reasons: MongoDB primary persistence, separate vector DB in MVP, Ollama in first provider slice, single local-user/no-auth design.

## Affected areas

- Components and interfaces: backend API/services, frontend UI, database schema/migrations, Docker Compose, tests, fixture data, documentation.
- Data and migrations: PostgreSQL schema, pgvector extension, user/project/import/profile/run/cluster/candidate/export/audit tables.
- Dependencies and configuration: PostgreSQL/pgvector driver/migration tooling, password hashing library, OpenAI/vLLM provider adapters, Docker Compose services.
- Deployment and operations: local Docker Compose only, persistent volumes, initial user seed, GPU default/CPU fallback documentation.
- Documentation: keep durable requirements/spec/ADRs current if material deviations occur.

## Risks and recovery

- Security/privacy: authentication, passwords, API keys, imported text, and audit trails require security-focused review. Use established password hashing; never return secrets/plaintext passwords.
- Compatibility/migration: schema migrations must be deterministic and testable; project data must remain isolated.
- Performance/reliability: vector/clustering path must avoid full pairwise all-record distance computation; background jobs must persist status/errors.
- Rollback/recovery: local MVP can recover by restoring persistent volumes/backups; project deletion is destructive after confirmation.

## Work items

| ID | Outcome | Status | Depends on | Task file |
|---|---|---|---|---|
| T001 | Local runtime, database, migrations, and baseline backend health | reviewed | none | `tasks/T001-local-runtime-db.md` |
| T002 | Authentication, equal-permission user management, initial user seed, and audit actor foundation | reviewed | T001 | `tasks/T002-auth-users-audit.md` |
| T003 | Project lifecycle and project isolation | reviewed | T001, T002 | `tasks/T003-project-lifecycle.md` |
| T004 | CSV/JSON import, dataset versions, and import logs | reviewed | T003 | `tasks/T004-import-datasets.md` |
| T005 | Global provider settings and project analysis profiles | reviewed | T002, T003 | `tasks/T005-providers-profiles.md` |
| T006 | Analysis-run job scaffold, embeddings/vector persistence seam, and run monitor | reviewed | T004, T005 | `tasks/T006-analysis-run-foundation.md` |
| T007 | Clustering foundation, cluster explorer, and source traceability | ready | T006 | `tasks/T007-cluster-explorer.md` |
| T008 | Candidate curation foundation and candidate editor | ready | T007 | `tasks/T008-candidate-curation.md` |
| T009 | Candidate/source CSV export and export history | ready | T008 | `tasks/T009-exports.md` |
| T010 | End-to-end UI shell, shared states, and fixture smoke coverage | ready | T002, T003, T004, T005 | `tasks/T010-ui-shell-smoke.md` |

## Acceptance-criteria traceability

| Criterion in durable requirement/specification | Work item | Automated verification |
|---|---|---|
| AC-1, AC-2 | T003 | Backend API/service tests; UI smoke where applicable |
| AC-3, AC-4, AC-5, AC-6, AC-7 | T004 | Import parser/service tests; fixture integration tests |
| AC-8, AC-9, AC-10 | T005 | Provider/profile API tests; secret readback tests |
| AC-11, AC-12, AC-13, AC-14, AC-15, AC-16 | T002 | Auth/user API tests; password-hash tests; audit tests |
| AC-17, AC-18 | T001 | Compose/schema/migration smoke tests; docs check |
| AC-19, AC-20, AC-21 | T006 | Job/run service tests; vector persistence tests |
| AC-22, AC-23, AC-24 | T007, T008 | Curation and traceability tests |
| AC-25, AC-26, AC-27 | T009 | Export schema tests; export metadata tests |
| AC-28 | T006, T010 | Local/stub profile workflow test |
| AC-29, AC-30, AC-31, AC-32, AC-33, AC-34, AC-35 | T010 plus feature tasks | UI smoke/component tests |

## Verification and closeout

- Focused commands: task-specific backend/frontend tests, lint/static checks, migration checks, docs check.
- Full command: `./.ai/tools/verify.sh`
- Specialist review required and why: security-focused review required for auth, password hashing, sessions, API-key handling, provider calls, file import parsing, and audit trail.
- Durable documentation/ADR updates: update requirements/spec/ADRs if task implementation changes scope, architecture, security posture, or public contracts.
- Temporary artifacts to remove after review: `.ai/work/support-knowledge-miner-mvp1/` after final reviewed closeout.

## Material deviations

- T002 technical decisions confirmed by the Decision Owner on 2026-07-22: use FastAPI for the local backend API, Argon2id via `argon2-cffi` for password hashing, and server-side database sessions with bearer tokens.
