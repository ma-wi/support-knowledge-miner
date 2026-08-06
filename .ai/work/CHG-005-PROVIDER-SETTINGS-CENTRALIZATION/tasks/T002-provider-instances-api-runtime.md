# Task T002: Provider-Instanzen, API und Runtime

- Status: in-progress
- Parent requirement or change: CHG-005-PROVIDER-SETTINGS-CENTRALIZATION
- Plan: `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/PLAN.md`
- Work type: incremental-change
- Review batch: RB002
- Depends on: T001
- Owner/agent: Codex
- Last updated: 2026-08-05

## Objective

Implement provider-instance persistence/API/runtime so active Provider can be added,
updated, deleted, checked and used by ID. Separate available models from selected
Embedding/LLM allow-lists. Remove vLLM from active backend provider support while
preserving historical provenance readability.

## Scope

- Migration for provider configuration IDs, display names, available model lists,
  selected Embedding/LLM allow-lists and provenance snapshot columns.
- OpenAI/Ollama provider create/update/delete/check/discover and Ollama pull
  endpoints.
- Provider service identity, default numbered names, hard delete and redacted audit.
- Remove active vLLM validation/runtime branches.
- Service/API/migration tests for this slice.

## Security Assurance

- Security assurance: required
- Triggers: secrets, local network endpoints, public API, migration, hard delete.
- Security triggers: secrets, local network endpoints, public API, migration, hard delete.
- Assets and data classes: OpenAI secret handles, local endpoint URLs,
  provider/model availability, model allow-lists, audit metadata, historical
  analysis/cluster provenance.
- Trust boundaries and untrusted inputs: browser payloads, endpoint/model names,
  provider responses, migrated database rows.
- Authorization model: existing authenticated API dependencies; provider settings
  remain global authenticated settings.
- Threats and abuse cases: secret disclosure, unsafe endpoint calls, duplicate display
  names used as identity, history loss after hard delete, stale model availability
  preserving unavailable models, raw provider diagnostics.
- Mitigations: write-only secrets, endpoint allow-listing, UUID identity,
  provenance snapshots, redacted Problem Details/audit, parameterized SQL.
- Security verification: negative tests for vLLM rejection, deletion/provenance and
  safe pull/check failure messages.
- Residual security risk: historical vLLM provenance may remain visible but is not
  accepted for active provider configuration or runtime calls.
- Specialist security review: required for provider secrets, local network calls,
  migration and hard delete behavior.

## Error and recovery implementation

### User actions covered

Provider create, update, delete, check and Ollama model pull.

### Expected failures

| Action | Failure | Error code | Safe user message | Placement | Recovery | Retry | Input preservation | Tests | Logging/correlation |
|---|---|---|---|---|---|---|---|---|---|
| Provider erstellen/speichern | validation or backend failure | `VALIDATION_FAILED`/`UNEXPECTED_ERROR` | Provider-Konfiguration konnte nicht gespeichert werden. Eingaben prüfen und erneut versuchen. | Provider card | Correct/retry | yes | Preserve non-secret fields and model ordering | API/service/frontend | redacted audit |
| Provider testen | endpoint/API-key unavailable | `VALIDATION_FAILED` or check `ok=false` | Verbindung konnte nicht geprüft werden. Endpoint/API-Key prüfen und erneut versuchen. | Provider card | Correct/retry | yes | Preserve non-secret fields and model allow-lists | API/service/frontend | redacted diagnostics |
| Provider entfernen | hard delete fails | `PROVIDER_DELETE_FAILED` | Provider konnte nicht entfernt werden. Historie bleibt erhalten; bitte erneut versuchen. | Provider card | Retry/reload | yes | No local draft loss | API/service | audit event/reference |
| Provider entfernen | active work still references provider | `PROVIDER_DELETE_BLOCKED` | Provider wird noch von einer aktiven Berechnung verwendet. Bitte Abschluss abwarten oder den Job abbrechen. | Provider card | Wait/cancel | yes after wait | No local draft loss | API/service | no cross-project job ID leak |
| Ollama-Modell laden | another pull running | `PROVIDER_MODEL_PULL_IN_PROGRESS` | Ein Modell-Download läuft bereits. Bitte Abschluss abwarten. | Ollama card | Wait | no | Preserve model input | API/service/frontend | redacted |
| Ollama-Modell laden | pull failed | `UNEXPECTED_ERROR` or provider validation | Ollama-Modell konnte nicht geladen werden. Modellname und Verbindung prüfen. | Ollama card | Retry | yes | Preserve model input | API/service/frontend | redacted |

### Unknown failure behavior

- User-facing fallback: safe provider action failure through `UNEXPECTED_ERROR` or
  the action-specific fallback text.
- Correlation ID: safe request/provider reference when available.
- Retry behavior: retry after correction/reload unless a pull is already active.
- Input preservation: preserve non-secret provider fields and model input; never
  echo OpenAI API keys.
- Support behavior: reload provider list and retry; inspect redacted server logs if
  local debugging is required.

### Required negative tests

- [x] vLLM provider creation/update is rejected.
- [x] provider validation returns safe `VALIDATION_FAILED` Problem Details.
- [x] provider deletion failure returns safe `PROVIDER_DELETE_FAILED` or `PROVIDER_DELETE_BLOCKED`.
- [x] concurrent Ollama pulls return `PROVIDER_MODEL_PULL_IN_PROGRESS`.
- [x] provider discovery stores available models separately from selected
  Embedding/LLM allow-lists and removes unavailable models after successful
  discovery.
- [x] OpenAI discovery classifies Embedding and LLM model candidates separately.
- [x] provider errors do not expose secrets or raw provider bodies.

## UI classification

- Design class: 3

## Component impact

### Existing components reused

- No direct production UI components changed in this backend slice.

### Existing components extended

- Provider forms are enabled by the new provider-instance API contract, explicit
  connection-test/discovery result and separate available-model state.

### New shared components

| Name/responsibility | Target path/layer | API/variants/states | Tests | Accessibility | Story/equivalent | Catalog entry |
|---|---|---|---|---|---|---|
| none | not-applicable | not-applicable | not-applicable | not-applicable | not-applicable | not-applicable |

### New feature-local components

- Not introduced in this backend slice.

### Components replaced or removed

- Active vLLM provider API/runtime support is removed from the provider service.

### Rejected reuse options

- Reusing provider type as identity was rejected because duplicate provider
  instances require stable IDs.

### Rationale

The backend API change preserves the approved UI model without introducing a
parallel frontend component in this task.

## Visual evidence

- Required screens: Provider tab and Ollama pull state after T004.
- Required states: default, validation failure, pull-in-progress, delete failure.
- Required viewports: desktop/mobile in production UI evidence.
- Manifest: deferred to T004/T005 because this slice has no standalone UI.

## Verification

- Targeted backend provider/API/migration tests.
- `git diff --check`.
- Evidence recorded before status advances to `verified`.
