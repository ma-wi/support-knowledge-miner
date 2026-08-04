# Error catalog

This catalog indexes the current active user-facing error contract. Add product and
capability-specific codes as behavior is implemented. The canonical rules and field
semantics are in `.ai/policies/USER_FACING_ERROR_HANDLING.md`.

## Catalog contract

Every active known code has exactly one entry with:

- Status: `active` or `deprecated`
- Category
- Trigger
- HTTP status or `not-applicable`
- Problem type
- User-facing title
- User-facing explanation
- Suggested action
- Suggested action code
- Retryable
- UI placement or `not-applicable`
- Input preservation
- Correlation reference
- Security considerations
- Backend source
- API contract
- Frontend mapping or `not-applicable`
- Required tests
- Replacement and removal criterion when deprecated

Codes use stable uppercase letters, digits, and underscores. General categories do
not hide a specific domain reason when that reason enables a better recovery action.

## Baseline categories

| Code | Default category | Typical status | Default recovery |
|---|---|---:|---|
| `VALIDATION_FAILED` | validation | 422 | correct-input |
| `AUTHENTICATION_REQUIRED` | authentication | 401 | reauthenticate |
| `PERMISSION_DENIED` | authorization | 403 | return or contact-support |
| `RESOURCE_NOT_FOUND` | not-found | 404 | return |
| `RESOURCE_CONFLICT` | conflict | 409 | correct-input or return |
| `CONCURRENT_MODIFICATION` | concurrent-modification | 409 | reload |
| `BUSINESS_RULE_VIOLATION` | business-rule | 422 | project-defined |
| `RATE_LIMITED` | rate-limit | 429 | retry |
| `DEPENDENCY_UNAVAILABLE` | dependency | 503 | retry |
| `REQUEST_TIMEOUT` | timeout | 504 | retry |
| `NETWORK_UNAVAILABLE` | network | not-applicable | retry |
| `OPERATION_CANCELLED` | cancellation | not-applicable | return |
| `UNEXPECTED_ERROR` | unexpected | 500 | retry or contact-support |

These rows define available categories, not automatically active product errors.
Active codes are declared below or indexed to a capability catalog.

## Active entries

### `UNEXPECTED_ERROR`

- Status: active
- Category: unexpected
- Trigger: An unclassified action failure reaches the user-facing boundary.
- HTTP status: 500
- Problem type: `urn:skm:error:UNEXPECTED_ERROR`
- User-facing title: Die Aktion konnte nicht abgeschlossen werden.
- User-facing explanation: Ein unerwarteter Fehler ist aufgetreten; die Eingaben bleiben soweit sicher erhalten.
- Suggested action: Bitte erneut versuchen oder den aktuellen Stand neu laden.
- Suggested action code: retry
- Retryable: yes
- UI placement: affected form, card, dialog, table, or page section
- Input preservation: Preserve safe input and current view state.
- Correlation reference: safe request or job identifier when available
- Security considerations: Do not expose stack traces, SQL, paths, secrets, raw support text, provider bodies, or credentials.
- Backend source: not-applicable: bound by owning CHG-004 implementation task
- API contract: not-applicable: FastAPI mapping tested by owning task
- Frontend mapping: not-applicable: central frontend normalizer updated by owning task
- Required tests: unknown-code and unexpected-error negative tests in owning task

### `INDEXING_MODEL_UNAVAILABLE`

- Status: active
- Category: validation
- Trigger: Selected embedding model is not configured or no longer available.
- HTTP status: 422
- Problem type: `urn:skm:error:INDEXING_MODEL_UNAVAILABLE`
- User-facing title: Die Indizierung wurde nicht gestartet.
- User-facing explanation: Das gewählte Embedding-Modell ist nicht verfügbar.
- Suggested action: Provider-Einstellungen prüfen oder ein anderes Modell wählen.
- Suggested action code: choose-model
- Retryable: yes
- UI placement: Indizierungsformular
- Input preservation: Preserve dataset, provider, model, and parameter selections.
- Correlation reference: safe request identifier
- Security considerations: Do not expose provider credentials or raw provider diagnostics.
- Backend source: not-applicable: T2 implementation owns mapping
- API contract: not-applicable: FastAPI mapping tested in T2
- Frontend mapping: not-applicable: frontend normalizer updated in T2
- Required tests: API/service/frontend negative tests

### `INDEXING_CLOUD_CONFIRMATION_REQUIRED`

- Status: active
- Category: business-rule
- Trigger: OpenAI indexing would send original text without explicit confirmation.
- HTTP status: 422
- Problem type: `urn:skm:error:INDEXING_CLOUD_CONFIRMATION_REQUIRED`
- User-facing title: Cloud-Nutzung muss bestätigt werden.
- User-facing explanation: Diese Indizierung würde Originaltexte an OpenAI senden.
- Suggested action: Cloud-Nutzung bestätigen oder ein lokales Modell wählen.
- Suggested action code: confirm-cloud-use
- Retryable: yes
- UI placement: Indizierungsformular
- Input preservation: Preserve all indexing form fields.
- Correlation reference: safe request identifier
- Security considerations: Do not send source text before confirmation.
- Backend source: not-applicable: T2 implementation owns mapping
- API contract: not-applicable: FastAPI mapping tested in T2
- Frontend mapping: not-applicable: frontend normalizer updated in T2
- Required tests: API/service/frontend confirmation tests

### `INDEXING_CANCEL_NOT_AVAILABLE`

- Status: active
- Category: conflict
- Trigger: Cancel is requested for an indexing job that is already terminal or not cancellable.
- HTTP status: 409
- Problem type: `urn:skm:error:INDEXING_CANCEL_NOT_AVAILABLE`
- User-facing title: Die Indizierung kann nicht abgebrochen werden.
- User-facing explanation: Die Indizierung ist bereits fertig, fehlgeschlagen oder abgebrochen.
- Suggested action: Liste aktualisieren und den aktuellen Status prüfen.
- Suggested action code: reload
- Retryable: yes
- UI placement: Indizierungskarte
- Input preservation: Preserve current list and selected filters.
- Correlation reference: safe job identifier
- Security considerations: Do not expose internal worker state.
- Backend source: not-applicable: T2 implementation owns mapping
- API contract: not-applicable: FastAPI mapping tested in T2
- Frontend mapping: not-applicable: frontend normalizer updated in T2
- Required tests: API/service/frontend cancellation tests

### `IMPORT_IN_USE_DELETED`

- Status: active
- Category: business-rule
- Trigger: Import deletion affects existing indexing runs or cluster sets.
- HTTP status: 200
- Problem type: `urn:skm:error:IMPORT_IN_USE_DELETED`
- User-facing title: Der Datensatz wurde als gelöscht markiert.
- User-facing explanation: Bestehende Indizierungen und Cluster-Sets bleiben erhalten und zeigen die gelöschte Quelle.
- Suggested action: Abhängige Artefakte prüfen oder mit anderer Quelle neu arbeiten.
- Suggested action code: review-dependencies
- Retryable: no
- UI placement: Importübersicht
- Input preservation: Preserve import list state.
- Correlation reference: audit event identifier
- Security considerations: Preserve project scope and do not delete derived artifacts unintentionally.
- Backend source: not-applicable: T2 implementation owns mapping
- API contract: not-applicable: FastAPI mapping tested in T2
- Frontend mapping: not-applicable: frontend normalizer updated in T2
- Required tests: API/service/frontend deletion tests

### `INDEXING_RUN_DELETED`

- Status: active
- Category: business-rule
- Trigger: Indexing deletion affects existing cluster sets.
- HTTP status: 200
- Problem type: `urn:skm:error:INDEXING_RUN_DELETED`
- User-facing title: Die Indizierung wurde als gelöscht markiert.
- User-facing explanation: Bestehende Cluster-Sets bleiben erhalten und zeigen die gelöschte Basis.
- Suggested action: Cluster-Sets prüfen oder mit anderer Basis neu clustern.
- Suggested action code: review-dependencies
- Retryable: no
- UI placement: Indizierungsübersicht
- Input preservation: Preserve indexing list state.
- Correlation reference: audit event identifier
- Security considerations: Preserve project scope and cluster-set traceability.
- Backend source: not-applicable: T2 implementation owns mapping
- API contract: not-applicable: FastAPI mapping tested in T2
- Frontend mapping: not-applicable: frontend normalizer updated in T2
- Required tests: API/service/frontend deletion tests

### `INDEXING_NOT_COMPLETE`

- Status: active
- Category: business-rule
- Trigger: A cluster-set action is requested from an incomplete indexing run.
- HTTP status: 422
- Problem type: `urn:skm:error:INDEXING_NOT_COMPLETE`
- User-facing title: Diese Indizierung ist noch nicht fertig.
- User-facing explanation: Nur fertige Indizierungen können als Basis verwendet werden.
- Suggested action: Fertigstellung abwarten oder eine fertige Indizierung wählen.
- Suggested action code: choose-completed-indexing
- Retryable: yes
- UI placement: Cluster-Set-Formular
- Input preservation: Preserve cluster parameters.
- Correlation reference: safe request identifier
- Security considerations: Do not create partial cluster-set writes.
- Backend source: `backend/clusters/service.py`, `backend/api/app.py`
- API contract: `backend/api/app.py` Cluster-Set Problem Details routes
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE`
- Required tests: cluster-set negative tests

### `CLUSTER_VECTOR_BASIS_UNAVAILABLE`

- Status: active
- Category: business-rule
- Trigger: Selected vector basis is unavailable for the chosen indexing run.
- HTTP status: 422
- Problem type: `urn:skm:error:CLUSTER_VECTOR_BASIS_UNAVAILABLE`
- User-facing title: Die Vektorbasis ist nicht verfügbar.
- User-facing explanation: Die gewählte Vektorbasis fehlt in dieser Indizierung.
- Suggested action: Andere Basis wählen oder neu indizieren.
- Suggested action code: choose-vector-basis
- Retryable: yes
- UI placement: Cluster-Set-Formular
- Input preservation: Preserve parameters.
- Correlation reference: safe request identifier
- Security considerations: Do not infer missing private data from other projects.
- Backend source: `backend/clusters/service.py`, `backend/api/app.py`
- API contract: `backend/api/app.py` Cluster-Set Problem Details routes
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE`
- Required tests: cluster-set vector-basis tests

### `CLUSTER_SUMMARY_SAMPLE_COUNT_INVALID`

- Status: active
- Category: validation
- Trigger: LLM sample count is not a positive integer.
- HTTP status: 422
- Problem type: `urn:skm:error:CLUSTER_SUMMARY_SAMPLE_COUNT_INVALID`
- User-facing title: Die Beispielanzahl ist ungültig.
- User-facing explanation: Die Anzahl der LLM-Beispiele muss mindestens 1 sein.
- Suggested action: Positive ganze Zahl eingeben oder alle Beispiele verwenden.
- Suggested action code: correct-input
- Retryable: yes
- UI placement: Cluster-Set-Formular
- Input preservation: Preserve all fields.
- Correlation reference: safe request identifier
- Security considerations: Reject before provider calls.
- Backend source: `backend/clusters/service.py`, `backend/api/app.py`
- API contract: `backend/api/app.py` Cluster-Set Problem Details routes
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE`
- Required tests: validation and UI input tests

### `CLUSTER_BUDGET_EXCEEDED`

- Status: active
- Category: business-rule
- Trigger: Clustering exceeds configured record/dimension/memory budget.
- HTTP status: 422
- Problem type: `urn:skm:error:CLUSTER_BUDGET_EXCEEDED`
- User-facing title: Die Clusterung ist zu groß.
- User-facing explanation: Die aktuelle Datenmenge oder Dimension überschreitet das Clusterbudget.
- Suggested action: Datenmenge oder Parameter reduzieren.
- Suggested action code: reduce-scope
- Retryable: yes
- UI placement: Cluster-Set-Formular
- Input preservation: Preserve all fields.
- Correlation reference: safe request identifier
- Security considerations: Report only safe capacity metadata.
- Backend source: `backend/clusters/service.py`, `backend/api/app.py`
- API contract: `backend/api/app.py` Cluster-Set Problem Details routes
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE`
- Required tests: capacity rejection tests

### `LLM_PROVIDER_UNAVAILABLE`

- Status: active
- Category: dependency
- Trigger: Selected LLM provider cannot be reached for summary generation.
- HTTP status: 503
- Problem type: `urn:skm:error:LLM_PROVIDER_UNAVAILABLE`
- User-facing title: Das LLM ist nicht erreichbar.
- User-facing explanation: Die Cluster wurden nicht vollständig zusammengefasst, weil der LLM-Provider nicht erreichbar ist.
- Suggested action: Provider prüfen, anderes LLM wählen oder ohne LLM fortfahren.
- Suggested action code: check-provider
- Retryable: yes
- UI placement: Cluster-Set-Status
- Input preservation: Preserve cluster assignments and parameters where safe.
- Correlation reference: safe job identifier
- Security considerations: Redact provider diagnostics and source text.
- Backend source: `backend/clusters/service.py`, `backend/providers/service.py`, `backend/api/app.py`
- API contract: `backend/api/app.py` Cluster-Set Problem Details routes
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE`
- Required tests: provider unavailable tests

### `LLM_CLOUD_CONFIRMATION_REQUIRED`

- Status: active
- Category: business-rule
- Trigger: OpenAI LLM summary generation would send original text without explicit confirmation.
- HTTP status: 422
- Problem type: `urn:skm:error:LLM_CLOUD_CONFIRMATION_REQUIRED`
- User-facing title: Cloud-Nutzung muss bestätigt werden.
- User-facing explanation: Diese Zusammenfassung würde Originaltexte an OpenAI senden.
- Suggested action: Cloud-Nutzung bestätigen, lokales LLM wählen oder ohne LLM fortfahren.
- Suggested action code: confirm-cloud-use
- Retryable: yes
- UI placement: Cluster-Set-Formular
- Input preservation: Preserve all cluster-set form fields.
- Correlation reference: safe request identifier
- Security considerations: Do not send source text before confirmation.
- Backend source: `backend/clusters/service.py`, `backend/providers/service.py`, `backend/api/app.py`
- API contract: `backend/api/app.py` Cluster-Set Problem Details routes
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE`
- Required tests: API/service/frontend confirmation tests

### `CLUSTER_SUMMARY_FAILED`

- Status: active
- Category: dependency
- Trigger: LLM output is invalid, oversized, timed out, or cannot be parsed safely.
- HTTP status: 422
- Problem type: `urn:skm:error:CLUSTER_SUMMARY_FAILED`
- User-facing title: Die Zusammenfassung konnte nicht erzeugt werden.
- User-facing explanation: Die Cluster wurden berechnet, aber die LLM-Zusammenfassung ist nicht sicher verwendbar.
- Suggested action: Erneut versuchen, anderes LLM wählen oder technische Cluster nutzen.
- Suggested action code: retry-summary
- Retryable: yes
- UI placement: Cluster-Set-Status und Tabellenzeile
- Input preservation: Preserve cluster assignments where safe.
- Correlation reference: safe job identifier
- Security considerations: Do not expose raw LLM body.
- Backend source: `backend/clusters/service.py`, `backend/providers/service.py`, `backend/api/app.py`
- API contract: `backend/api/app.py` Cluster-Set Problem Details routes
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE`
- Required tests: invalid LLM output tests

### `CLUSTER_SET_CANCEL_NOT_AVAILABLE`

- Status: active
- Category: conflict
- Trigger: Cancel is requested for a terminal or non-cancellable cluster-set job.
- HTTP status: 409
- Problem type: `urn:skm:error:CLUSTER_SET_CANCEL_NOT_AVAILABLE`
- User-facing title: Das Cluster-Set kann nicht abgebrochen werden.
- User-facing explanation: Der Job ist bereits fertig, fehlgeschlagen oder abgebrochen.
- Suggested action: Liste aktualisieren und Status prüfen.
- Suggested action code: reload
- Retryable: yes
- UI placement: Cluster-Set-Karte
- Input preservation: Preserve tree state.
- Correlation reference: safe job identifier
- Security considerations: Do not expose worker internals.
- Backend source: `backend/clusters/service.py`, `backend/api/app.py`
- API contract: `backend/api/app.py` Cluster-Set Problem Details routes
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE`
- Required tests: cluster-set cancellation tests

### `CLUSTER_SET_NOT_FOUND`

- Status: active
- Category: not-found
- Trigger: Cluster set is missing or not project-scoped to the requester.
- HTTP status: 404
- Problem type: `urn:skm:error:CLUSTER_SET_NOT_FOUND`
- User-facing title: Das Cluster-Set wurde nicht gefunden.
- User-facing explanation: Das Cluster-Set wurde gelöscht oder gehört nicht zu diesem Projekt.
- Suggested action: Liste neu laden oder ein anderes Set wählen.
- Suggested action code: reload
- Retryable: yes
- UI placement: Cluster-Set-Übersicht oder Explorer
- Input preservation: Preserve safe filters where possible.
- Correlation reference: safe request identifier
- Security considerations: Do not reveal cross-project existence.
- Backend source: `backend/clusters/service.py`, `backend/api/app.py`
- API contract: `backend/api/app.py` Cluster-Set Problem Details routes
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE`
- Required tests: not-found and project-scope tests

### `CLUSTER_SET_NOT_COMPLETE`

- Status: active
- Category: conflict
- Trigger: Explorer clusters are requested before the Cluster-Set has completed.
- HTTP status: 409
- Problem type: `urn:skm:error:CLUSTER_SET_NOT_COMPLETE`
- User-facing title: Das Cluster-Set ist noch nicht fertig.
- User-facing explanation: Das Cluster-Set kann erst nach Abschluss geladen werden.
- Suggested action: Status aktualisieren und Abschluss abwarten.
- Suggested action code: wait
- Retryable: yes
- UI placement: Cluster-Set-Übersicht oder Explorer
- Input preservation: Preserve selected Cluster-Set and filters.
- Correlation reference: safe request identifier
- Security considerations: Do not expose partial cluster rows as loadable results.
- Backend source: `backend/clusters/service.py`, `backend/api/app.py`
- API contract: `backend/api/app.py` Cluster-Set Problem Details routes
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE`
- Required tests: cluster-set completion gate tests

### `CLUSTER_RUN_BOUND_API_REPLACED`

- Status: active
- Category: conflict
- Trigger: Deprecated run-bound cluster generation or loading route is called.
- HTTP status: 410
- Problem type: `urn:skm:error:CLUSTER_RUN_BOUND_API_REPLACED`
- User-facing title: Run-bound Clustering wurde ersetzt.
- User-facing explanation: Cluster werden jetzt ausschließlich über Cluster-Sets erzeugt und geladen.
- Suggested action: Ein Cluster-Set erstellen.
- Suggested action code: create-cluster-set
- Retryable: no
- UI placement: not-applicable: legacy route is no longer rendered in the UI
- Input preservation: Preserve caller state where applicable.
- Correlation reference: safe request identifier
- Security considerations: Prevent derived clusters from bypassing Cluster-Set lifecycle, lineage and safe errors.
- Backend source: `backend/api/app.py`
- API contract: `backend/api/app.py` deprecated cluster routes
- Frontend mapping: not-applicable: legacy route is no longer rendered in the UI
- Required tests: legacy route replacement tests

### `CLUSTER_SOURCE_NOT_FOUND`

- Status: active
- Category: not-found
- Trigger: Cluster source dialog target is missing or out of scope.
- HTTP status: 404
- Problem type: `urn:skm:error:CLUSTER_SOURCE_NOT_FOUND`
- User-facing title: Die Quellen konnten nicht geladen werden.
- User-facing explanation: Der Cluster wurde nicht gefunden oder gehört nicht zum geladenen Set.
- Suggested action: Cluster-Set neu laden.
- Suggested action code: reload
- Retryable: yes
- UI placement: Quellen-Dialog
- Input preservation: Preserve explorer filters.
- Correlation reference: safe request identifier
- Security considerations: Do not expose cross-project source existence.
- Backend source: `backend/clusters/service.py`, `backend/api/app.py`
- API contract: `backend/api/app.py` source-dialog Problem Details mapping;
  `docs/api/problem-details-contract.yaml`
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE`
- Required tests: source-dialog not-found tests

### `CLUSTER_SOURCE_PAGE_INVALID`

- Status: active
- Category: validation
- Trigger: Cluster source dialog pagination parameters are invalid or outside the bounded contract.
- HTTP status: 422
- Problem type: `urn:skm:error:CLUSTER_SOURCE_PAGE_INVALID`
- User-facing title: Die Quellen-Seite ist ungültig.
- User-facing explanation: Die Quellen konnten mit diesen Seitenparametern nicht geladen werden.
- Suggested action: Dialog neu öffnen oder Seitenparameter korrigieren.
- Suggested action code: correct-input
- Retryable: yes
- UI placement: Quellen-Dialog
- Input preservation: Preserve Explorer filters and loaded source rows where safe.
- Correlation reference: safe request identifier
- Security considerations: Keep source-dialog raw text responses page-bounded.
- Backend source: `backend/clusters/service.py`, `backend/api/app.py`
- API contract: `backend/api/app.py` source-dialog Problem Details mapping;
  `docs/api/problem-details-contract.yaml`
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE`
- Required tests: source-dialog pagination validation tests

### `CLUSTER_MANUAL_UPDATE_INVALID`

- Status: active
- Category: validation
- Trigger: A manual cluster title, category or status update contains invalid values.
- HTTP status: 422
- Problem type: `urn:skm:error:CLUSTER_MANUAL_UPDATE_INVALID`
- User-facing title: Cluster-Änderung ist ungültig.
- User-facing explanation: Die manuellen Clusterwerte konnten nicht gespeichert werden.
- Suggested action: Eingaben prüfen und erneut speichern.
- Suggested action code: correct-input
- Retryable: yes
- UI placement: Explorer table row/global feedback
- Input preservation: Preserve table, filters and entered manual values where safe.
- Correlation reference: safe request identifier
- Security considerations: Do not expose cross-project cluster existence or raw database details.
- Backend source: `backend/clusters/service.py`
- API contract: `backend/api/app.py` cluster manual update Problem Details mapping
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE`
- Required tests: cluster manual-update API and frontend negative tests

### `CLUSTER_REFINEMENT_EMPTY_SOURCE`

- Status: active
- Category: business-rule
- Trigger: Refinement is requested without included sources.
- HTTP status: 422
- Problem type: `urn:skm:error:CLUSTER_REFINEMENT_EMPTY_SOURCE`
- User-facing title: Keine Quellen für die Verfeinerung.
- User-facing explanation: Für die Verfeinerung ist mindestens ein eingeschlossener Cluster erforderlich.
- Suggested action: Mindestens einen Cluster einschließen.
- Suggested action code: select-sources
- Retryable: yes
- UI placement: Refinement panel
- Input preservation: Preserve parameters.
- Correlation reference: safe request identifier
- Security considerations: Do not create empty child sets.
- Backend source: `backend/clusters/service.py`, `backend/api/app.py`
- API contract: `backend/api/app.py` cluster-set refinement Problem Details mapping;
  `docs/api/problem-details-contract.yaml`
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE`
- Required tests: refinement validation tests

### `CLUSTER_SEARCH_NO_RESULTS`

- Status: active
- Category: validation
- Trigger: Explorer text search/filter yields no visible cluster rows.
- HTTP status: not-applicable
- Problem type: `urn:skm:error:CLUSTER_SEARCH_NO_RESULTS`
- User-facing title: Keine Treffer.
- User-facing explanation: Keine Cluster entsprechen der aktuellen Textsuche oder dem Filter.
- Suggested action: Suchtext oder Filter anpassen.
- Suggested action code: adjust-filter
- Retryable: yes
- UI placement: Explorer table empty state
- Input preservation: Preserve search and filters.
- Correlation reference: not-applicable
- Security considerations: Do not log sensitive search text unnecessarily.
- Backend source: not-applicable: UI state owned by explorer task
- API contract: not-applicable
- Frontend mapping: not-applicable: explorer task owns UI behavior
- Required tests: explorer empty-state tests

### `EXPLORER_EXPORT_EMPTY`

- Status: active
- Category: validation
- Trigger: Explorer export is requested when current filters produce no rows.
- HTTP status: 422
- Problem type: `urn:skm:error:EXPLORER_EXPORT_EMPTY`
- User-facing title: Es gibt nichts zu exportieren.
- User-facing explanation: Im aktuellen Filterstand gibt es keine exportierbaren Zeilen.
- Suggested action: Filter anpassen oder Suche löschen.
- Suggested action code: adjust-filter
- Retryable: yes
- UI placement: Explorer Export-Abschnitt
- Input preservation: Preserve search/filter state.
- Correlation reference: safe request identifier
- Security considerations: Do not create empty misleading files.
- Backend source: `backend/exports/service.py`, `backend/api/app.py`
- API contract: `backend/api/app.py` Explorer export Problem Details mapping;
  `docs/api/problem-details-contract.yaml`
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE`
- Required tests: export empty-state tests

### `EXPLORER_EXPORT_FORMAT_INVALID`

- Status: active
- Category: validation
- Trigger: Explorer export is requested with a format other than CSV or JSON.
- HTTP status: 422
- Problem type: `urn:skm:error:EXPLORER_EXPORT_FORMAT_INVALID`
- User-facing title: Das Exportformat ist ungültig.
- User-facing explanation: Der Explorer kann nur als CSV oder JSON exportiert werden.
- Suggested action: CSV oder JSON wählen.
- Suggested action code: choose-format
- Retryable: yes
- UI placement: Explorer Export-Abschnitt
- Input preservation: Preserve search/filter state and selected format control.
- Correlation reference: safe request identifier
- Security considerations: Do not fall back to an implicit or misleading file format.
- Backend source: `backend/exports/service.py`, `backend/api/app.py`
- API contract: `backend/api/app.py` Explorer export Problem Details mapping;
  `docs/api/problem-details-contract.yaml`
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE`
- Required tests: export format validation tests

### `EXPLORER_EXPORT_SELECTION_TOO_LARGE`

- Status: active
- Category: validation
- Trigger: Explorer export selection exceeds the maximum supported cluster count.
- HTTP status: 422
- Problem type: `urn:skm:error:EXPLORER_EXPORT_SELECTION_TOO_LARGE`
- User-facing title: Die Exportauswahl ist zu groß.
- User-facing explanation: Die aktuelle Explorer-Auswahl enthält zu viele Cluster.
- Suggested action: Filter oder Auswahl verkleinern.
- Suggested action code: reduce-scope
- Retryable: yes
- UI placement: Explorer Export-Abschnitt
- Input preservation: Preserve search/filter state.
- Correlation reference: safe request identifier
- Security considerations: Keep export generation memory and response size bounded.
- Backend source: `backend/exports/service.py`, `backend/api/app.py`
- API contract: `backend/api/app.py` Explorer export Problem Details mapping;
  `docs/api/problem-details-contract.yaml`
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE`
- Required tests: export selection-size validation tests

### `EXPLORER_EXPORT_FAILED`

- Status: active
- Category: unexpected
- Trigger: CSV or JSON export generation fails after validation.
- HTTP status: 500
- Problem type: `urn:skm:error:EXPLORER_EXPORT_FAILED`
- User-facing title: Der Export konnte nicht erstellt werden.
- User-facing explanation: Die gefilterte Explorer-Ansicht konnte nicht als Datei erzeugt werden.
- Suggested action: Erneut versuchen oder ein anderes Format wählen.
- Suggested action code: retry
- Retryable: yes
- UI placement: Explorer Export-Abschnitt
- Input preservation: Preserve search/filter state.
- Correlation reference: safe request identifier
- Security considerations: Do not include raw source texts unless explicitly requested.
- Backend source: `backend/exports/service.py`, `backend/api/app.py`
- API contract: `backend/api/app.py` Explorer export Problem Details mapping;
  `docs/api/problem-details-contract.yaml`
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE`
- Required tests: export failure tests

### `DISPLAY_NAME_SAVE_FAILED`

- Status: active
- Category: dependency
- Trigger: Autosave of a project/import/indexing/cluster-set display name fails.
- HTTP status: 503
- Problem type: `urn:skm:error:DISPLAY_NAME_SAVE_FAILED`
- User-facing title: Der Name konnte nicht gespeichert werden.
- User-facing explanation: Die Namensänderung wurde nicht dauerhaft gespeichert.
- Suggested action: Erneut versuchen oder Liste neu laden.
- Suggested action code: retry
- Retryable: yes
- UI placement: Inline am Namensfeld
- Input preservation: Preserve typed name until reload.
- Correlation reference: safe request identifier
- Security considerations: Do not expose resource IDs outside project scope.
- Backend source: not-applicable: owning implementation task maps resource type
- API contract: not-applicable: FastAPI mapping tested by owning task
- Frontend mapping: not-applicable: frontend normalizer updated by owning task
- Required tests: autosave failure tests

### `CLUSTER_OUTLIER_EMPTY_RESULT`

- Status: active
- Category: business-rule
- Trigger: Outlier threshold would remove every source from consideration.
- HTTP status: 422
- Problem type: `urn:skm:error:CLUSTER_OUTLIER_EMPTY_RESULT`
- User-facing title: Keine Quellen nach Ausreißer-Ausschluss.
- User-facing explanation: Mit diesem Threshold bleiben keine auswertbaren Quellen übrig.
- Suggested action: Threshold reduzieren.
- Suggested action code: adjust-threshold
- Retryable: yes
- UI placement: Ausreißer-Box
- Input preservation: Preserve outlier parameters.
- Correlation reference: safe request identifier
- Security considerations: Do not write empty child set.
- Backend source: `backend/clusters/service.py`, `backend/api/app.py`
- API contract: `backend/api/app.py` outlier/refinement Problem Details mapping;
  `docs/api/problem-details-contract.yaml`
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE`
- Required tests: outlier validation tests

### `CLUSTER_OUTLIER_RECALCULATION_FAILED`

- Status: active
- Category: dependency
- Trigger: Outlier exclusion calculation fails after validation.
- HTTP status: 500
- Problem type: `urn:skm:error:CLUSTER_OUTLIER_RECALCULATION_FAILED`
- User-facing title: Ausreißer konnten nicht ausgeschlossen werden.
- User-facing explanation: Der Ausreißer-Ausschluss konnte nicht abgeschlossen werden.
- Suggested action: Parameter prüfen oder erneut versuchen.
- Suggested action code: retry
- Retryable: yes
- UI placement: Ausreißer-Box
- Input preservation: Preserve outlier parameters.
- Correlation reference: safe job identifier
- Security considerations: Do not expose clustering internals or raw text.
- Backend source: `backend/clusters/service.py`, `backend/api/app.py`
- API contract: `backend/api/app.py` outlier/refinement Problem Details mapping;
  `docs/api/problem-details-contract.yaml`
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE`
- Required tests: outlier failure tests

### `CLUSTER_SET_LINEAGE_UNAVAILABLE`

- Status: active
- Category: dependency
- Trigger: Cluster-set lineage or history cannot be loaded.
- HTTP status: 503
- Problem type: `urn:skm:error:CLUSTER_SET_LINEAGE_UNAVAILABLE`
- User-facing title: Die Herkunft konnte nicht geladen werden.
- User-facing explanation: Das Cluster-Set bleibt nutzbar, aber die Historie konnte nicht geladen werden.
- Suggested action: Historie erneut laden oder Parent direkt öffnen.
- Suggested action code: retry
- Retryable: yes
- UI placement: Cluster-Set-Baum oder Explorer-Analysepfad
- Input preservation: Preserve loaded set and table state.
- Correlation reference: safe request identifier
- Security considerations: Do not expose hidden parent from another project.
- Backend source: `backend/clusters/service.py`, `backend/api/app.py`
- API contract: `backend/api/app.py` Cluster-Set Problem Details routes
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE`
- Required tests: lineage failure tests

## Entry template

### `CUSTOMER_VERSION_CONFLICT`

- Status: active
- Category: concurrent modification
- Trigger: The submitted version differs from the current persisted version.
- HTTP status: 409
- Problem type: `https://example.test/problems/customer-version-conflict`
- User-facing title: Der Kunde wurde nicht gespeichert.
- User-facing explanation: Der Datensatz wurde zwischenzeitlich geändert.
- Suggested action: Laden Sie den aktuellen Stand und wiederholen Sie Ihre Änderung.
- Suggested action code: reload
- Retryable: yes-after-reload
- UI placement: form-banner
- Input preservation: Preserve unsaved input until the user confirms reload.
- Correlation reference: optional
- Security considerations: Do not disclose another editor's identity unless allowed.
- Backend source: `CustomerVersionConflict`
- API contract: OpenAPI `ProblemDetails` response for customer update
- Frontend mapping: central `ApplicationError` mapping
- Required tests:
  - backend mapping test
  - API contract test
  - frontend mapping test
  - interaction test

The entry above is a template example and is not an active code until a project
removes this sentence and declares it in an active capability.

## Capability catalogs

None.

## Deprecated entries

None.
