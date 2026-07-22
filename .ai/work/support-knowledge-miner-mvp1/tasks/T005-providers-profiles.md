# Task T005: Global provider settings and project analysis profiles

- Status: ready
- Parent requirement: support-knowledge-miner-mvp1
- Plan: `.ai/work/support-knowledge-miner-mvp1/PLAN.md`
- Depends on: T002, T003
- Owner/agent: implementer
- Last updated: 2026-07-19

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

- [ ] Spec AC-8: Global provider settings support OpenAI API-key entry/replacement and vLLM endpoint/model discovery or manual model list.
- [ ] Spec AC-9: Project can contain multiple analysis profiles, each selecting a globally configured model with independent thresholds/parameters.
- [ ] Spec AC-10: Stored OpenAI API keys cannot be retrieved in plaintext through normal read interfaces.
- [ ] Spec AC-31: UI supports global provider settings behavior.

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

- [ ] Focused tests
- [ ] Relevant linting and static analysis
- [ ] Security or dependency checks when applicable
- [ ] Documentation assessment

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

## Result

