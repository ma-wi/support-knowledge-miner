# Task T007: Optional RAPIDS/cuML dependency extras

- Status: verified
- Parent requirement or change: CHG-005-PROVIDER-SETTINGS-CENTRALIZATION
- Plan: `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/PLAN.md`
- Work type: incremental-change
- Review batch: RB007
- Depends on: T006
- Owner/agent: Codex
- Last updated: 2026-08-06

## Objective

Make RAPIDS/cuML installable through locked Python extras without making GPU/CUDA a
mandatory dependency for the default local backend runtime.

## Scope

- Add mutually exclusive `gpu-cu12` and `gpu-cu13` optional dependencies.
- Update `uv.lock`.
- Document install/run commands and CUDA-version selection.
- Do not change clustering behavior beyond enabling the already implemented
  dynamic cuML imports to resolve when the matching extra is installed.

## Security Assurance

- Security assurance: required
- Security triggers: dependency/build chain and native GPU runtime packages.
- Assets and data classes: local Python environment, package lockfile, CUDA runtime
  libraries, imported support vectors processed by local clustering.
- Trust boundaries and untrusted inputs: public PyPI packages and transitive native
  wheels; no production resources.
- Authorization model: not-applicable: local dependency install only.
- Threats and abuse cases: supply-chain compromise, wrong CUDA package installed,
  accidental hard GPU dependency breaking CPU-only installs.
- Mitigations: bounded optional extras, `uv.lock` integrity, mutually exclusive
  extras, default CPU install unchanged, safe runtime fallback/error already in T006.
- Security verification: `uv lock --dry-run`, dependency policy/audit, security gate
  and full verify.
- Residual security risk: RAPIDS/cuML pulls many native transitive packages; users
  must choose the CUDA-major extra matching their local NVIDIA runtime.
- Specialist security review: completed through independent read-only review on
  2026-08-06.

## Dependency review

- Packages: `cuml-cu12>=26.6,<26.7` and `cuml-cu13>=26.6,<26.7`.
- Ecosystem/source: PyPI; owner shown as NVIDIA; cuML repository license is
  Apache-2.0.
- Purpose: optional GPU acceleration for HDBSCAN/UMAP paths already guarded by
  dynamic imports.
- Existing alternatives: CPU scikit-learn path remains default and fallback.
- Native/transitive impact: substantial CUDA/RAPIDS native wheel set, including
  cuDF, RMM, RAFT, CuPy and NVIDIA CUDA libraries.
- Locking: `uv.lock` updated; extras are mutually exclusive through `tool.uv`.
- Exit strategy: remove optional extras; application continues on CPU backend.

## Error and recovery implementation

### User actions covered

- Other: local dependency installation and backend start with optional GPU extra.

### Expected failures

| Error code | Trigger | Backend mapping | UI placement | User message | Recovery |
|---|---|---|---|---|---|
| not-applicable | No new API/UI action or error code | Existing T006 `CLUSTER_ACCELERATOR_UNAVAILABLE` when forced cuML is unusable | Existing Cluster-Set card/form | Existing safe accelerator-unavailable message | Install matching extra or select CPU/auto |

### Unknown failure behavior

- User-facing fallback: unchanged from T006.
- Correlation ID: unchanged.
- Retry behavior: install matching extra or use CPU backend.
- Input preservation: unchanged Cluster-Set form behavior.
- Support behavior: inspect sanitized Cluster-Set diagnostics.

### Required negative tests

- [x] Dependency unavailable: covered by T006 forced-cuML tests.
- [x] No false success feedback: default run confirms cuML is not silently present.
- [x] Other categories: not-applicable; no new user-facing action.

### Error acceptance criteria

- [x] Existing accelerator-unavailable mapping remains the user-facing recovery path.
- [x] No raw CUDA/import stack traces are exposed by this dependency-only change.

## UI classification

- Design class: 3
- Prototype strategy: none
- Visual review required: no

## Component impact

### Existing components reused

- Existing Cluster-Set backend selector and error rendering from T006.

### Existing components extended

- None.

### New shared components

| Name/responsibility | Target path/layer | API/variants/states | Tests | Accessibility | Story/equivalent | Catalog entry |
|---|---|---|---|---|---|---|
| none | not-applicable | not-applicable | not-applicable | not-applicable | not-applicable | not-applicable |

### New feature-local components

- None.

### Components replaced or removed

- None.

### Rejected reuse options

- Hard default dependency was rejected because it would make CPU-only setup depend
  on NVIDIA/CUDA packages.

### Rationale

The production UI is unchanged; this task only makes the existing dynamic cuML
runtime path installable.

## Visual evidence

- Required screens: not-applicable.
- Required states: not-applicable.
- Required viewports: not-applicable.
- Manifest: not-applicable.

## Acceptance criteria

- [x] `pyproject.toml` exposes a locked CUDA 12 and CUDA 13 cuML install option.
- [x] Default `uv run --locked python -m backend.main` remains CPU-compatible and
  does not require cuML.
- [x] Documentation explains how to install and run with the matching extra.
- [x] Dependency/security/full verification pass.

## Verification

- `UV_PYTHON=3.13 uv lock --dry-run` — passed.
- `UV_PYTHON=3.13 uv sync --locked --extra gpu-cu13 --dry-run` — passed; would
  install 47 GPU packages and replace NumPy with the RAPIDS-compatible lock fork.
- `UV_PYTHON=3.13 uv sync --locked --extra gpu-cu12 --dry-run` — passed; `--all-extras`
  correctly fails because CUDA 12/13 extras conflict.
- `UV_PYTHON=3.13 uv run --locked python - <<'PY' ...` — passed; cuML is not
  available in the default environment.
- `./.ai/tools/check-dependencies.sh` — passed; 37 direct dependency entries,
  no known vulnerabilities from configured scanners.
- `./.ai/tools/format.sh --check` and `./.ai/tools/lint.sh` — passed.
- `./.ai/tools/verify.sh` — passed on final rerun; 225 backend tests, 45 frontend
  tests, 5 Bats tests, dependency policy/audit, security and build included.

## Result

RAPIDS/cuML is now available as locked optional CUDA 12/13 extras. Default setup and
default backend start remain CPU-compatible; users install one matching extra when
GPU acceleration is desired.

### Adversarial pre-review

- Adversarial pre-review: passed
- Pre-review lenses: dependency policy, runtime compatibility, default install
  compatibility, supply-chain risk.
- Pre-review evidence: optional extras are mutually exclusive and locked; default
  `uv run --locked` does not expose cuML; CUDA 13 dry-run is resolvable; no new UI/API
  path is added.
- Open P0/P1 findings: none

### Independent review

- Review type: independent read-only dependency/security review.
- Reviewer: independent Codex subagent `Confucius`.
- Review date: 2026-08-06.
- Review scope: T007 task file, plan/current work state, optional RAPIDS/cuML
  dependency extras, `pyproject.toml`, `uv.lock`, README/deployment docs,
  relevant cluster runtime/error docs and tests.
- Review verdict: approved for T007.
- Findings:
  - P0/P1: none.
  - P2: work-state/closeout was not clean because T007 was still listed as
    `in-progress` in the plan/current pointer and T008 had an invalid
    `Security assurance: required.` value. Fixed during mechanical closeout.
  - P3: README used machine-specific CUDA wording. Replaced with generic example
    wording during mechanical closeout.
- Review evidence: reviewer confirmed optional extras are not default
  dependencies, `tool.uv.conflicts` makes CUDA 12/13 extras mutually exclusive,
  `uv.lock` includes locked optional RAPIDS/cuML dependency trees, default CPU
  compatibility is preserved, and the user-facing failure path remains the safe
  `CLUSTER_ACCELERATOR_UNAVAILABLE` mapping.

## Review outcome

- T007 implementation: complete.
- Verification: complete; full `./.ai/tools/verify.sh` evidence recorded above.
- Independent review: complete with no open P0/P1 findings.
- Mechanical review closeout: task status, plan status, current-plan pointer and
  related documentation hygiene reconciled on 2026-08-06.
- Final status deferral: CHG-005 is Design Class 3. The repository UI-quality gate
  does not allow task status `reviewed` or `done` before the approved CHG-005 visual
  review, and it does not allow this task to understate the parent design class.
  T007 therefore remains `verified` with independent review documented until the
  overall CHG-005 visual-review phase advances the task statuses.
