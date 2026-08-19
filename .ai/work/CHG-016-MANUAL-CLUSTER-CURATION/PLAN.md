# Implementation plan: Manuelle Cluster-Kuration und direkte Explorer-Bearbeitung

- Status: draft
- Change class: significant
- Work type: incremental-change
- Requirement: `docs/requirements/chg-016-manual-cluster-curation.md`
- Change request: `.ai/work/CHG-016-MANUAL-CLUSTER-CURATION/CHANGE.md`
- Change impact: `.ai/work/CHG-016-MANUAL-CLUSTER-CURATION/IMPACT.md`
- Canonical capability specifications: `docs/specifications/support-knowledge-miner-mvp1.md`
- Work directory: `.ai/work/CHG-016-MANUAL-CLUSTER-CURATION/`
- Last updated: 2026-08-19

## Outcome and implementation boundary

- In scope: Manuelles leeres/beispielbasiertes Cluster, LLM-Startwerte,
  Einzel-Cluster-LLM-Aktualisierung, referenzbasierte Embedding-Match-Vorschau,
  bestätigte Membership-Zuweisung, Inline-Autosave für fünf Clusterfelder und
  Source-to-Outlier-Move.
- Non-goals: neue Kandidatenpipeline, externe Fuzzy-Abhängigkeit, automatische
  fachliche Freigabe, Produktions-/Live-Integrationen.
- Accepted assumptions: bestehende Provider-/Embedding-/Summary-Grenzen,
  projektbezogene Auth, `manual_edit` als bestehender Owner.
- Open blockers: D001–D011, API-/Migration-Detail, genehmigte Klasse-2-Direction.

## Current-state findings and approach

- Relevant owners: `ClusterService` owns Cluster-Set/Membership/summary logic;
  FastAPI owns contracts/errors; `App.tsx` owns Explorer interaction; existing
  Provider/Analysis services own LLM/embedding calls.
- Desired end state: generated sets immutable; first manual structural edit creates
  a mutable manual-edit child (D001); all manual fields and source moves are
  transactional and recoverable.
- Existing responsibility decision: extend, never create a parallel cluster or
  membership store.
- Proposed implementation: migration for manual FAQ overrides/versioning; bounded
  manual create/preview/move and single-cluster-summary service methods/routes;
  reference IDs plus basis/scope search contract; central error mapping; inline UI
  state with rollback; local class-2 form/preview composition.
- New artifacts: only routes/payloads, migration fields and feature-local UI state;
  each extends an existing owner and has removal criteria in `IMPACT.md`.
- Rejected: `SequenceMatcher` as primary semantic search; mutation of generated
  sets; a second membership table; row-level separate Save form.

## Affected areas

- Components/interfaces: `backend/api/app.py`, `backend/clusters/service.py`,
  `backend/analysis/service.py`/provider boundary, `frontend/src/App.tsx/.css`.
- Data/migrations: clusters manual FAQ effective fields, manual-edit lifecycle and
  conflict/version data only if required by D001; no rewrite of existing sets.
- Dependencies/configuration: no new dependency planned; use existing numpy/pgvector/
  provider stack and existing UI-quality tooling.
- Deployment/operations: local Docker/PostgreSQL only; migration before app rollout;
  no production access.
- Documentation: requirement, CHANGE/IMPACT closeout, capability spec, API contract,
  error catalog, design catalog only if a reusable component is introduced.

## UI classification

- Design class: 2
- Rationale: new multi-step creation/preview flow; inline edits and source action
  extend established Explorer patterns.
- Highest design class assigned: 2
- Implementation-start design class: not-started
- Prototype strategy: isolated-prototype or approved React mock prototype
- Prototype artifact/revision: pending
- Required tool dependencies and owning package: existing frontend UI-quality setup
- Existing pattern/components reused: Explorer table, source dialog, form controls,
  focus management, status chips, feedback overlays.
- Applicable design-system rule: `docs/design/DESIGN_SYSTEM.md` table/dialog/form,
  responsive and accessibility rules.
- Design approval status: pending
- Visual review required: yes
- Required screens/states: empty/manual form, example/LLM loading/error, single-
  cluster LLM refresh pending/error/success, reference selection and search preview/
  no-result, create success/error, inline save success/error, source move
  success/error, desktop/mobile/focus/long-text.
- Required viewports: 1440x1000 and 390x844.

## Error-handling strategy

Authoritative matrix: `CHANGE.md` Error-and-Recovery Matrix. New actions use stable
codes for create validation, examples, single-cluster summary generation, reference
selection/search, match preview, empty results, conflict and source move. All paths
enter the central API normalizer and frontend mapping; optimistic writes roll back;
unknown failures use the safe fallback. Error catalog/API contract/frontend mappings
and negative tests are part of T001–T003.

## Risks and recovery

- Compatibility/migration: additive nullable manual fields and backward-compatible
  payloads; generated sets untouched. If D001 is rejected, use an explicitly
  approved alternative before implementation.
- Performance/reliability: bound example count/length, candidate scope, dimensions,
  result count, provider prompt/output and local execution; no all-pairs matrix.
- Rollback/recovery: transactional manual child/membership operation, conflict
  rejection, parent preservation and safe UI rollback.

## Security Assurance routing

- Security assurance: required
- Security triggers: confidential support data, public/project API mutation, LLM
  network/provider boundary, untrusted LLM/text input, resource exhaustion and
  irreversible-looking membership changes.
- Threat model: `.ai/work/CHG-016-MANUAL-CLUSTER-CURATION/THREAT_MODEL.md`
- Specialist security review: required; verify project authorization, provider
  consent, prompt/response redaction, bounds, replay/idempotency and mutation
  recovery before independent review.

## Review cadence

- Cadence: per-task
- Maximum tasks per review batch: 1
- Forced per-task triggers: migration, public-api, security
- Rationale: schema/API/membership mutation and sensitive text handling each require
  an independently reviewed verifiable slice.

## Work items

| ID | Vertical outcome | Status | Depends on | Review batch | Impact rows closed | Task file |
|---|---|---|---|---|---|---|
| T001 | Manual-edit domain, persistence, create/preview, single-summary and reference-search contracts | draft | D001–D011 | RB001 | schema, domain, API, security, error rows | `tasks/T001-manual-cluster-domain-api.md` |
| T002 | Explorer manual-cluster flow, single-cluster LLM action, reference search and inline autosave | draft | T001 + design approval | RB002 | UI, frontend, error/UI evidence rows | `tasks/T002-explorer-manual-flow-and-inline-editing.md` |
| T003 | Source-to-Outlier move and manual-child refresh lifecycle | draft | T001 + D001 | RB003 | membership, source dialog, recovery rows | `tasks/T003-source-to-outlier-curation.md` |

## Acceptance-criteria traceability

| Criterion in durable requirement/specification | Work item | Automated verification |
|---|---|---|
| AC-1, AC-2, AC-3, AC-4, AC-5, AC-8, AC-9, AC-11, AC-12 | T001 | service/API/migration/provider/security tests |
| AC-6, AC-13 | T002 | frontend/API rollback, focus, accessibility and browser tests |
| AC-7, AC-8, AC-9 | T003 | transaction, auth/conflict/replay and source-dialog tests |
| AC-10 | T001–T003 | focused gates, `verify.sh`, independent code/security/visual review |

## Superseded-artifact and canonical-spec closeout

- Superseded artifacts: row-level Save form removed by T002; auto-summary-only
  editing assumption replaced by manual FAQ overrides; no parallel membership store.
- Repository-wide orphan searches: `Speichern`, `auto_summary_question`,
  `manual_edit`, new error codes, source move endpoint, old/new API fields.
- Capability specification: update `support-knowledge-miner-mvp1.md` in place.
- Temporary compatibility: automatic summary fields remain; remove only when an
  accepted API version explicitly replaces them.

## Verification and closeout

- Focused commands: targeted backend/API/service/migration tests; frontend tests;
  `./.ai/tools/check-user-facing-errors.py`; UI browser/accessibility/visual commands.
- Full command: `./.ai/tools/verify.sh`
- Specialist review: security review plus independent code review; independent
  visual review required for class 2.
- Durable documentation: requirement acceptance, capability spec, API contract,
  error catalog, design catalog only if component reuse changes; assess README and
  `.ai/PROJECT_CONTEXT.md` for current behavior.
- Temporary artifacts: remove active work directory after accepted closeout,
  including prototype/evidence unless retention is explicitly approved.

## Material deviations

- None; D001–D011 changes must be recorded before implementation readiness.
