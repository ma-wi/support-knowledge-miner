# Current work

- Work type: incremental-change
- Requirement: current user request from 2026-08-05
- Work directory: `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/`
- Change request: `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/CHANGE.md`
- Change impact: `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/IMPACT.md`
- Specifications: `docs/specifications/local-runtime-providers.md`, `docs/specifications/support-knowledge-miner-mvp1.md`
- Plan: `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/PLAN.md`
- Status: implementation
- Current task or review batch: `T008` verified after remediation; independent
  review and required browser/accessibility/visual evidence remain pending.
- Orchestrator item: not-orchestrated
- Design delta: `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/DESIGN_DELTA.md`
- Visual evidence: required after production UI implementation
- Error handling: required
- Error catalog: `docs/errors/ERROR_CATALOG.md`
- Security assurance: required because provider settings include secrets, local network endpoints, migration and irreversible active-provider deletion
- Last updated: 2026-08-06

## Latest focused evidence

- Planning-only update on 2026-08-06: added `T008` for Explorer left control rail,
  top-right global menu overlay and Summary regeneration placement. No production
  implementation was authorized or performed.
- Readiness update on 2026-08-06: Product Owner released `T008` for future
  implementation.
- T007 review outcome on 2026-08-06: independent read-only dependency/security
  review approved T007 with no open P0/P1 findings. T007 remains `verified` because
  CHG-005's Design Class 3 UI-quality gate blocks `reviewed`/`done` until visual
  review.
- T008 remediation on 2026-08-06: persistent left global sidebar removed from all
  signed-in layouts; Cluster-Set and Explorer Summary actions open the Option-A
  provider/model/sample/result dialog; Summary response parsing accepts common LLM
  labeled-text and typographic-quote variants.
- Focused evidence for T008:
  `npm --prefix frontend test -- --run App.test.tsx` — passed, 46 tests.
- Focused evidence for T008:
  `PYTHONPATH=. uv run pytest tests/clusters/test_cluster_service.py -q` — passed,
  55 tests.
- Focused evidence for T008: `./.ai/tools/format.sh --check`,
  `./.ai/tools/lint.sh`, and `cd frontend && npm run build` — passed.
- Full evidence for T008: `./.ai/tools/verify.sh` — passed; 225 backend tests,
  46 frontend tests and 5 Bats tests included.
- Pending T008 evidence: desktop/mobile browser evidence, accessibility review and
  visual regression/review after remediation.

- Previous focused evidence before T006: analysis/API tests, frontend App tests and
  frontend build passed.
- Direct local Ollama diagnostic: `bge-m3:latest` first 12 provider batches passed
  with line-break normalization plus lowercase for both replace/remove modes.
- Focused evidence for T006:
  `PYTHONPATH=. UV_PYTHON=3.13 uv run --locked pytest tests/clusters/test_cluster_service.py tests/api/test_cluster_api_integration.py tests/providers/test_provider_model_discovery.py` — passed, 90 tests.
- Focused evidence for T006:
  `npm test -- --run src/App.test.tsx` from `frontend/` — passed, 45 tests.
- Focused evidence for T006: `./.ai/tools/format.sh --check`,
  `./.ai/tools/lint.sh`, and `./.ai/tools/check-user-facing-errors.py` — passed.
- Full evidence for T006: `./.ai/tools/verify.sh` — passed; 223 backend tests,
  45 frontend tests and 5 Bats tests included.
- Full evidence for T007: `./.ai/tools/verify.sh` — passed; 225 backend tests,
  45 frontend tests and 5 Bats tests included.
