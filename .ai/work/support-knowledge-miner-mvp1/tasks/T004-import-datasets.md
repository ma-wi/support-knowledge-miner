# Task T004: CSV/JSON import, dataset versions, and import logs

- Status: verified
- Parent requirement: support-knowledge-miner-mvp1
- Plan: `.ai/work/support-knowledge-miner-mvp1/PLAN.md`
- Depends on: T003
- Owner/agent: implementer
- Last updated: 2026-07-22

## Objective

Implement project-scoped CSV/JSON import for already-paired records, immutable dataset versions, skipped-record import logs, and synthetic fixtures.

## Scope

### In scope

- CSV parser for headers `ticketid`, `messagegroupid`, `message`, `answer`.
- JSON parser for root list of objects with equivalent fields.
- Per-record validation for required fields and non-empty `message`/`answer`.
- Duplicate `ticketid` + `messagegroupid` accepted.
- Dataset version persistence.
- Import log persistence and UI summary/detail workflow.
- Synthetic CSV/JSON fixtures.

### Out of scope

- Pair inference from ticket timelines.
- Analysis execution.
- Deduplication by semantic/content similarity.

## Preconditions

- T003 complete.

## Affected files or components

- Backend import/dataset modules.
- Database migrations.
- Frontend import screen/log view.
- Fixture files and tests.

## Acceptance criteria

- [x] Spec AC-3: Valid CSV imports into selected project and creates immutable dataset version.
- [x] Spec AC-4: Valid JSON imports with equivalent behavior.
- [x] Spec AC-5: Missing CSV headers, malformed JSON, and non-list JSON roots fail before dataset creation and produce an import log.
- [x] Spec AC-6: Invalid records are skipped/logged; duplicate `ticketid` + `messagegroupid` records are accepted.
- [x] Spec AC-7: Zero-valid-record import creates no dataset version and reports clear failure summary.
- [x] Spec AC-32: Import UI shows counts and persisted log access.

## Implementation constraints

- Treat uploaded/imported files as untrusted input.
- Bound file sizes and parsing resource usage where practical.
- Do not log secrets; minimize raw text in error summaries unless needed in detailed import log.

## Applicable specification and test seam

- Specification criteria: AC-3 through AC-7, AC-32.
- Primary observable boundary for this task: import API/service and import UI workflow.
- Implementation-specific boundaries to avoid testing directly: parser helper internals beyond edge-case tests.

## Verification

- [x] Focused tests
- [x] Relevant linting and static analysis
- [x] Security or dependency checks when applicable
- [x] Documentation assessment

Exact commands:

```bash
./.ai/tools/test.sh
./.ai/tools/security.sh
./.ai/tools/lint.sh
python .ai/tools/check-docs.py
```

## Risks or blockers

- File parsing is an untrusted-input boundary and requires security-focused review.

## Result

- Added project-scoped import persistence for immutable dataset versions, message pairs, import logs, and skipped-record entries.
- Added authenticated import API endpoints for CSV/JSON import, project import-log listing, and persisted log-entry detail access.
- Added frontend import workflow that reads selected CSV/JSON files, reports counts, shows dataset-version IDs, and loads persisted skipped-record details.
- Added synthetic CSV/JSON fixtures plus parser/service/API/migration/frontend tests and a local Docker smoke script covering valid CSV, valid JSON, invalid rows, duplicate identifiers, and file-level failures without dataset creation.
- Verification observed on 2026-07-22:
  `./.ai/tools/format.sh --check`,
  `./.ai/tools/lint.sh`,
  `./.ai/tools/test.sh`,
  `deployment/docker/scripts/smoke-imports.sh`,
  `./.ai/tools/verify.sh`.
