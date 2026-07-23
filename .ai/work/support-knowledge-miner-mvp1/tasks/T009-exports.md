# Task T009: Candidate/source CSV export and export history

- Status: reviewed
- Parent requirement: support-knowledge-miner-mvp1
- Plan: `.ai/work/support-knowledge-miner-mvp1/PLAN.md`
- Depends on: T008
- Owner/agent: implementer
- Last updated: 2026-07-23

## Objective

Implement candidate and source-assignment CSV exports using accepted baseline columns, export metadata persistence, and export UI warnings for original/potentially identifying text.

## Scope

### In scope

- Candidate CSV export with accepted baseline columns.
- Source-assignment CSV export with accepted baseline columns.
- Export metadata persistence in project database.
- Export history UI.
- Warning/toggle behavior for exports including original text where applicable.
- Tests for exact CSV headers and traceability fields.

### Out of scope

- Optional cluster/audit exports unless already trivial and explicitly scoped.
- Project archive export/import.

## Preconditions

- T008 complete.

## Affected files or components

- Backend export modules.
- Database migrations if needed.
- Frontend export screen/history.
- Tests.

## Acceptance criteria

- [x] Spec AC-25: Candidate CSV export exactly includes accepted baseline columns.
- [x] Spec AC-26: Source-assignment CSV export exactly includes accepted baseline columns.
- [x] Spec AC-27: Export metadata is persisted and records whether original text was included.
- [x] Spec AC-35: Export UI warns when original/potentially identifying text is included and records export metadata.

## Implementation constraints

- CSV output must be deterministic enough for tests.
- Escape CSV fields correctly.
- Avoid leaking secrets or unrelated project data.

## Applicable specification and test seam

- Specification criteria: AC-25, AC-26, AC-27, AC-35.
- Primary observable boundary for this task: export API/service and export UI.
- Implementation-specific boundaries to avoid testing directly: CSV writer internals beyond output contract.

## Verification

- [x] Focused tests
- [x] Relevant linting and static analysis
- [x] Security or dependency checks when applicable
- [x] Documentation assessment

Exact commands:

```bash
./.ai/tools/test.sh
./.ai/tools/lint.sh
python .ai/tools/check-docs.py
```

## Risks or blockers

- Exports may include original text; UI warning and metadata must be reliable.

## Result

- Implemented project-scoped candidate CSV and source-assignment CSV exports through
  `ExportService` and authenticated API endpoints.
- Added `export_logs` migration with export type, filters/selection placeholders,
  dataset/run references, output filename/path, row count, actor, timestamp, and
  `include_original_text`.
- Candidate CSV and source-assignment CSV headers match the accepted baseline
  columns exactly; source-assignment original text fields are blank unless explicitly
  included.
- Added export UI actions, original-text warnings, last CSV preview, and project
  export history.
- Documentation assessed: `README.md` and `.ai/PROJECT_CONTEXT.md` reviewed on
  2026-07-23; no durable update needed because the accepted specification already
  owns the export contract and Project Context already records export persistence and
  traceability.
- Verification passed:
  - `./.ai/tools/test.sh`
  - `./.ai/tools/format.sh --check`
  - `./.ai/tools/lint.sh`
  - `python .ai/tools/check-docs.py`
  - `./.ai/tools/verify.sh`
- Residual risk: requires independent review before advancing beyond `verified`.
- Remediated review P2 by making candidate export original-text metadata
  conservative: cluster/source-derived candidates force persisted
  `include_original_text=true`, CSV `contains_original_text=true`, and a warning
  even when the request checkbox is unset. Source-assignment redaction semantics
  remain unchanged.
- Added service, API, and frontend regression coverage for a candidate export
  requested with `include_original_text=false` where the actual candidate export is
  returned and persisted as containing original text.
- Remediation verification passed:
  - `uv run --locked python -m pytest tests/exports/test_export_service.py tests/api/test_export_api_integration.py`
  - `npm test -- --run src/App.test.tsx`
  - `./.ai/tools/format.sh --check`
  - `./.ai/tools/lint.sh`
  - `./.ai/tools/test.sh`
  - `python .ai/tools/check-docs.py`
- Re-review approved on 2026-07-23; task advanced to `reviewed`.
