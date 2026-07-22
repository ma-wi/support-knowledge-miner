# Task T005: Global provider settings and project analysis profiles

- Status: reviewed
- Parent requirement: support-knowledge-miner-mvp1
- Plan: `.ai/work/support-knowledge-miner-mvp1/PLAN.md`
- Depends on: T002, T003
- Owner/agent: implementer
- Last updated: 2026-07-22

## Objective

Implement global OpenAI/vLLM provider settings and project-scoped analysis profiles that select globally configured models and store analysis parameters.

## Scope

### In scope

- Global OpenAI provider settings with API-key set/replace/remove and write-only read behavior.
- Global vLLM provider settings with endpoint and model discovery/manual model configuration.
- Provider connection/model-list checks using safe timeouts.
- Project-scoped analysis profiles selecting a globally configured model.
- Profile parameters: thresholds, algorithm settings, prompt/prompt identifiers where applicable.
- UI screens for global provider settings and project analysis profiles.

### Out of scope

- Running model inference beyond connection/model-list checks.
- Live OpenAI dependency in mandatory tests.
- Multiple local providers beyond vLLM.

## Preconditions

- T002 and T003 complete.
- ADR-0003 accepted.

## Affected files or components

- Backend provider/profile modules.
- Database migrations.
- Frontend global provider settings and analysis profile UI.
- Provider adapter tests/stubs.

## Acceptance criteria

- [x] Spec AC-8: Global provider settings support OpenAI API-key entry/replacement and vLLM endpoint/model discovery or manual model list.
- [x] Spec AC-9: Project can contain multiple analysis profiles, each selecting a globally configured model with independent thresholds/parameters.
- [x] Spec AC-10: Stored OpenAI API keys cannot be retrieved in plaintext through normal read interfaces.
- [x] Spec AC-31: UI supports global provider settings behavior.

## Implementation constraints

- Do not require live OpenAI in mandatory tests.
- Secrets are write-only after save.
- Use explicit cloud-use indicators for OpenAI model selections.
- Bound provider connection-test timeouts.

## Applicable specification and test seam

- Specification criteria: AC-8 through AC-10, AC-31.
- Primary observable boundary for this task: provider/profile backend APIs and UI workflows.
- Implementation-specific boundaries to avoid testing directly: HTTP client internals.

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

- API-key handling requires security-focused review.
- Provider network calls must be explicit and bounded.
- Direct dependency: `cryptography>=48,<49` is used for Fernet authenticated encryption of stored provider credentials because Python's standard library does not provide a vetted symmetric encryption primitive. It is a widely maintained PyCA package under Apache-2.0/BSD licensing with locked hashes in `uv.lock`; `pip-audit` passed after upgrading to `48.0.1` for GHSA-537c-gmf6-5ccf. Replacement strategy if it becomes unsuitable: move provider credentials to an OS/local secret store adapter and remove encrypted database storage.

## Result

- Added global provider persistence for OpenAI and vLLM, including OpenAI API-key set/replace/remove with write-only API responses and vLLM endpoint/manual-model configuration.
- Added authenticated provider API endpoints for listing configuration summaries, upserting provider settings, and bounded provider checks.
- Added project-scoped analysis profiles that select configured provider/model pairs and persist thresholds, algorithm settings, and prompt identifiers.
- Added UI workflows for global provider settings and project analysis-profile creation, including explicit OpenAI cloud-use labeling.
- Added migration/API/UI/smoke coverage for provider settings, secret non-readback, model selection, profile persistence, and cloud/local profile distinction.
- Remediated review P1 by encrypting OpenAI API keys with Fernet before database storage. Saving provider credentials now requires `SKM_PROVIDER_ENCRYPTION_KEY`; read APIs/UI remain write-only and regression tests fail if the submitted key is stored verbatim.
- Remediated review P2 by removing copied agent prompt transcript content from `README.md`; maintained documentation no longer ships temporary workflow/chat text.
- Added local configuration documentation for generating the provider credential encryption key without committing it.
- Verification observed on 2026-07-22:
  `./.ai/tools/format.sh --check`,
  `./.ai/tools/lint.sh`,
  `./.ai/tools/test.sh`,
  `./.ai/tools/security.sh`,
  `python .ai/tools/check-docs.py`,
  `deployment/docker/scripts/smoke-providers-profiles.sh`,
  `./.ai/tools/verify.sh`.
