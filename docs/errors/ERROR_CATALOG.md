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
| `PROJECT_NOT_FOUND` | not-found | 404 | reload |
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

### `CLUSTER_TAXONOMY_FAILED`

- Status: active
- Category: dependency
- Trigger: Die ausgewählten Parent-Cluster enthalten keine vollständigen Summaries oder ein LLM liefert keine formal auswertbare Taxonomie-JSON-Struktur; fehlende, doppelte und unbekannte Zuordnungen in einer formal gültigen Struktur werden lokal verlustfrei normalisiert.
- HTTP status: 422 for synchronous validation; background jobs persist the code.
- Problem type: `urn:skm:error:CLUSTER_TAXONOMY_FAILED`
- User-facing title: Die Cluster-Taxonomie konnte nicht erstellt werden.
- User-facing explanation: Die Parent-Summaries sind unvollständig oder die LLM-Antwort konnte nicht sicher den Quellclustern zugeordnet werden.
- Suggested action: Parent-Summaries und Provider prüfen und ein neues Child starten.
- Suggested action code: retry
- Retryable: yes
- UI placement: Cluster-Set-Karte und Explorer-Kontext
- Input preservation: Parent-Cluster-Set und Formularauswahl bleiben erhalten.
- Correlation reference: sichere Cluster-Set- oder Request-ID
- Security considerations: Keine Rohantwort, Prompts, Supporttexte oder unbekannten IDs anzeigen oder loggen.
- Backend source: `backend/clusters/service.py`; `backend/api/app.py`
- API contract: `docs/api/problem-details-contract.yaml`
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE`
- Required tests: Parserstruktur-, Partitionsreparatur-, Feldgrenz-, Provider- und UI-Fallbacktests

### `CLUSTER_LLM_ASSIGNMENT_FAILED`

- Status: active
- Category: dependency
- Trigger: Die ausgewählte Parent-Taxonomie enthält keine vollständigen Summaries
  oder das LLM liefert malformed JSON, eine falsche Root-/Objektstruktur oder
  falsche Feldtypen. Fehlende, doppelte oder unbekannte IDs sind kein Trigger;
  sie werden deterministisch repariert.
- HTTP status: 422 for synchronous validation; background jobs persist the code.
- Problem type: `urn:skm:error:CLUSTER_LLM_ASSIGNMENT_FAILED`
- User-facing title: Die LLM-Clusterzuordnung konnte nicht erstellt werden.
- User-facing explanation: Die Taxonomie ist unvollständig oder die LLM-Antwort
  konnte nicht sicher allen Supportpaaren zugeordnet werden.
- Suggested action: Taxonomie und Provider prüfen und ein neues Child starten.
- Suggested action code: retry
- Retryable: yes
- UI placement: Cluster-Set-Karte und Explorer-Kontext
- Input preservation: Parent-Cluster-Set und Formularauswahl bleiben erhalten.
- Correlation reference: sichere Cluster-Set- oder Request-ID
- Security considerations: Keine Rohantwort, Prompts, Supporttexte oder unbekannten IDs anzeigen oder loggen.
- Backend source: `backend/clusters/service.py`; `backend/api/app.py`
- API contract: `docs/api/problem-details-contract.yaml`
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE`
- Required tests: formale Parserfehler, semantische Partitionsreparatur,
  Ausreißer-Persistenz, Provider- und UI-Fallbacktests

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

### `VALIDATION_FAILED`

- Status: active
- Category: validation
- Trigger: A submitted form/API payload for a user-triggered action is syntactically or domain-invalid, including a project LLM-taxonomy budget outside its documented hard bounds.
- HTTP status: 422
- Problem type: `urn:skm:error:VALIDATION_FAILED`
- User-facing title: Die Eingaben sind ungültig.
- User-facing explanation: Die Aktion wurde nicht ausgeführt, weil Eingaben korrigiert werden müssen.
- Suggested action: Eingaben prüfen und erneut versuchen.
- Suggested action code: correct-input
- Retryable: yes
- UI placement: affected form or provider card, including inline project-settings fields
- Input preservation: Preserve safe non-secret fields; never echo API keys or provider credentials.
- Correlation reference: safe request identifier
- Security considerations: Do not expose validation internals, endpoint credentials, provider bodies or secrets.
- Backend source: `backend/api/app.py`
- API contract: `docs/api/problem-details-contract.yaml`
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE`
- Required tests: provider/project API validation tests, field association, input preservation and frontend normalizer mapping tests

### `PROJECT_NOT_FOUND`

- Status: active
- Category: not-found
- Trigger: A user-triggered project settings or lifecycle action targets a project that is no longer available.
- HTTP status: 404
- Problem type: `urn:skm:error:PROJECT_NOT_FOUND`
- User-facing title: Das Projekt wurde nicht gefunden.
- User-facing explanation: Die Projektaktion wurde nicht ausgeführt, weil das Projekt nicht mehr verfügbar ist.
- Suggested action: Projektliste neu laden.
- Suggested action code: reload
- Retryable: yes
- UI placement: project settings form or affected project page section
- Input preservation: Preserve safe local draft fields until navigation or reload.
- Correlation reference: safe request identifier when available
- Security considerations: Do not expose internal IDs beyond the user-selected local project context.
- Backend source: `backend/projects/service.py`; `backend/api/app.py`
- API contract: `backend/api/app.py` project Problem Details mapping
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE` and project settings form mapping
- Required tests: project API not-found Problem Details test and project settings negative UI tests

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
- Trigger: Vector clustering exceeds its configured record, dimension or memory
  budget, summary generation exceeds its prompt budget, or an LLM-taxonomy job
  exceeds its snapshotted project budget. LLM taxonomy assignment has no separate
  total-pair budget.
- HTTP status: 422
- Problem type: `urn:skm:error:CLUSTER_BUDGET_EXCEEDED`
- User-facing title: Die Clusterung ist zu groß.
- User-facing explanation: Die aktuelle Datenmenge, Dimension oder Zusammenfassung überschreitet das Clusterbudget. Bei einer LLM-Taxonomie verweist die Meldung auf das passende Projektlimit unter Einstellungen.
- Suggested action: Datenmenge, Dimensionen oder Beispiele reduzieren oder bei einer LLM-Taxonomie das passende Projektlimit unter Einstellungen erhöhen und ein neues Child starten.
- Suggested action code: reduce-scope
- Retryable: yes
- UI placement: Cluster-Set-Formular oder Cluster-Set-Status
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
- Trigger: Selected LLM provider cannot be reached or returns an explicitly
  incomplete/unusable generation response.
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
- Required tests: provider unavailable and incomplete-response tests

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

### `CLUSTER_REDUCTION_UNAVAILABLE`

- Status: active
- Category: dependency
- Trigger: A Cluster-Set requests UMAP/PCA reduction parameters that cannot be applied in the local runtime.
- HTTP status: 422
- Problem type: `urn:skm:error:CLUSTER_REDUCTION_UNAVAILABLE`
- User-facing title: Dimensionsreduzierung ist nicht verfügbar.
- User-facing explanation: Die gewählte Dimensionsreduzierung ist lokal nicht verfügbar.
- Suggested action: Parameter anpassen oder eine installierte Reduktionsmethode wählen.
- Suggested action code: adjust-clustering-parameters
- Retryable: yes
- UI placement: Cluster-Set-Formular und Cluster-Set-Status
- Input preservation: Preserve clustering parameters.
- Correlation reference: safe job identifier
- Security considerations: Do not expose local import paths or stack traces.
- Backend source: `backend/clusters/service.py`, `backend/api/app.py`
- API contract: `backend/api/app.py` Cluster-Set Problem Details routes
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE`
- Required tests: HDBSCAN reduction parameter tests

### `CLUSTER_ACCELERATOR_UNAVAILABLE`

- Status: active
- Category: dependency
- Trigger: A Cluster-Set requests the cuML GPU backend, but RAPIDS/cuML or a compatible GPU runtime is unavailable.
- HTTP status: 422
- Problem type: `urn:skm:error:CLUSTER_ACCELERATOR_UNAVAILABLE`
- User-facing title: GPU-Beschleunigung ist nicht verfügbar.
- User-facing explanation: cuML/RAPIDS ist in dieser lokalen Laufzeit nicht verfügbar.
- Suggested action: CPU-Backend wählen oder lokale RAPIDS/cuML-Installation prüfen.
- Suggested action code: choose-cpu-backend
- Retryable: yes
- UI placement: Cluster-Set-Formular und Cluster-Set-Status
- Input preservation: Preserve clustering parameters.
- Correlation reference: safe job identifier
- Security considerations: Do not expose CUDA driver paths or stack traces.
- Backend source: `backend/clusters/service.py`, `backend/api/app.py`
- API contract: `backend/api/app.py` Cluster-Set Problem Details routes
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE`
- Required tests: cuML backend fallback/error tests

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

### `CLUSTER_ALGORITHM_PARAMETERS_INVALID`

- Status: active
- Category: validation
- Trigger: Cluster-Set creation or refinement receives parameters that are incompatible with the selected algorithm or refinement mode.
- HTTP status: 422
- Problem type: `urn:skm:error:CLUSTER_ALGORITHM_PARAMETERS_INVALID`
- User-facing title: Die Cluster-Parameter sind ungültig.
- User-facing explanation: Die Parameter passen nicht zum gewählten Algorithmus oder Verfeinerungsmodus.
- Suggested action: Parameter korrigieren und erneut starten.
- Suggested action code: correct-input
- Retryable: yes
- UI placement: Cluster-Set-Formular
- Input preservation: Preserve cluster-set form fields and selected refinement sources.
- Correlation reference: safe request identifier
- Security considerations: Do not expose estimator internals, stack traces, paths, SQL, embeddings or raw support text.
- Backend source: `backend/clusters/service.py` algorithm/refinement validation
- API contract: `backend/api/app.py` Cluster-Set Problem Details mapping
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE`
- Required tests: algorithm parameter validation API/service/frontend tests

### `CLUSTER_BATCH_REFINEMENT_EMPTY_GROUP`

- Status: active
- Category: business-rule
- Trigger: Per-parent batch refinement contains a selected parent cluster with no usable source pairs.
- HTTP status: 422
- Problem type: `urn:skm:error:CLUSTER_BATCH_REFINEMENT_EMPTY_GROUP`
- User-facing title: Eine Parent-Gruppe hat keine Quellen.
- User-facing explanation: Mindestens ein ausgewählter Parent-Cluster enthält keine nutzbaren Quellen.
- Suggested action: Auswahl prüfen oder den leeren Parent-Cluster ausschließen.
- Suggested action code: select-sources
- Retryable: yes
- UI placement: Cluster-Set-Formular und Cluster-Set-Status
- Input preservation: Preserve selected parent clusters and clustering parameters.
- Correlation reference: safe request or job identifier
- Security considerations: Do not expose raw support text or cross-project cluster existence.
- Backend source: `backend/clusters/service.py` per-parent refinement preflight
- API contract: `backend/api/app.py` Cluster-Set Problem Details mapping;
  `docs/api/problem-details-contract.yaml`
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE`
- Required tests: per-parent batch empty-group API/service/frontend tests

### `CLUSTER_BATCH_REFINEMENT_GROUP_INVALID`

- Status: active
- Category: validation
- Trigger: Per-parent batch refinement has at least one parent group that is too small or otherwise incompatible with the selected algorithm parameters.
- HTTP status: 422
- Problem type: `urn:skm:error:CLUSTER_BATCH_REFINEMENT_GROUP_INVALID`
- User-facing title: Eine Parent-Gruppe kann nicht verfeinert werden.
- User-facing explanation: Eine Parent-Gruppe ist für die gewählten Cluster-Parameter zu klein oder ungültig.
- Suggested action: Parameter senken, andere Cluster wählen oder den Parent-Cluster separat prüfen.
- Suggested action code: adjust-clustering-parameters
- Retryable: yes
- UI placement: Cluster-Set-Formular und Cluster-Set-Status
- Input preservation: Preserve selected parent clusters and clustering parameters.
- Correlation reference: safe request or job identifier
- Security considerations: Report safe counts/IDs only for current-project resources; do not expose embeddings or raw support text.
- Backend source: `backend/clusters/service.py` per-parent group execution
- API contract: `backend/api/app.py` Cluster-Set Problem Details mapping;
  `docs/api/problem-details-contract.yaml`
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE`
- Required tests: per-parent batch invalid-group API/service/frontend tests

### `CLUSTER_SET_DUPLICATE_UNAVAILABLE`

- Status: active
- Category: conflict
- Trigger: Cluster-Set duplicate is requested for a non-completed, missing,
  deleted, non-project-scoped, or otherwise unavailable source set.
- HTTP status: 409
- Problem type: `urn:skm:error:CLUSTER_SET_DUPLICATE_UNAVAILABLE`
- User-facing title: Das Cluster-Set kann nicht dupliziert werden.
- User-facing explanation: Das ausgewählte Cluster-Set ist nicht mehr für eine Duplikation verfügbar.
- Suggested action: Cluster-Set-Liste neu laden und ein verfügbares Set wählen.
- Suggested action code: reload
- Retryable: yes
- UI placement: Cluster-Set-Karte
- Input preservation: Preserve Cluster-Set list selection where safe.
- Correlation reference: safe request identifier
- Security considerations: Do not reveal cross-project existence or raw source data.
- Backend source: `backend/clusters/service.py` duplicate Cluster-Set action
- API contract: `backend/api/app.py` duplicate Cluster-Set route;
  `docs/api/problem-details-contract.yaml`
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE`
- Required tests: running cluster-set rejection in service/API/frontend plus
  duplicate conflict mapping tests

### `CLUSTER_SET_BATCH_DELETE_FAILED`

- Status: active
- Category: conflict
- Trigger: Cluster-Set batch delete cannot delete every selected set under all-or-nothing semantics.
- HTTP status: 409
- Problem type: `urn:skm:error:CLUSTER_SET_BATCH_DELETE_FAILED`
- User-facing title: Cluster-Sets konnten nicht gelöscht werden.
- User-facing explanation: Die ausgewählten Cluster-Sets konnten nicht vollständig gelöscht werden.
- Suggested action: Auswahl prüfen, Liste neu laden und erneut versuchen.
- Suggested action code: reload
- Retryable: yes
- UI placement: Cluster-Set-Batch-Toolbar
- Input preservation: Preserve selected Cluster-Set IDs that remain visible and safe.
- Correlation reference: safe request identifier
- Security considerations: Do not reveal cross-project existence; do not partially delete after a failed all-or-nothing request.
- Backend source: `backend/clusters/service.py` batch delete action
- API contract: `backend/api/app.py` batch delete route;
  `docs/api/problem-details-contract.yaml`
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE`
- Required tests: all-or-nothing cluster-set batch delete API/frontend tests

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

### `PROVIDER_MODEL_PULL_IN_PROGRESS`

- Status: active
- Category: conflict
- Trigger: An Ollama model pull is requested while another Ollama model pull is already active.
- HTTP status: 409
- Problem type: `urn:skm:error:PROVIDER_MODEL_PULL_IN_PROGRESS`
- User-facing title: Ein Modell-Download läuft bereits.
- User-facing explanation: Ein Ollama-Modell wird bereits geladen.
- Suggested action: Abschluss abwarten und danach erneut versuchen.
- Suggested action code: wait
- Retryable: no-until-complete
- UI placement: Ollama provider card download row and feedback overlay
- Input preservation: Preserve the entered model name while the request is blocked.
- Correlation reference: safe request identifier
- Security considerations: Do not expose endpoint details or raw Ollama response bodies.
- Backend source: `backend/providers/service.py`, `backend/api/app.py`
- API contract: `docs/api/problem-details-contract.yaml`
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE`
- Required tests: provider service/API/frontend pull-in-progress tests

### `PROVIDER_DELETE_FAILED`

- Status: active
- Category: not-found
- Trigger: A provider delete request targets a provider that cannot be removed from active configuration.
- HTTP status: 404
- Problem type: `urn:skm:error:PROVIDER_DELETE_FAILED`
- User-facing title: Provider konnte nicht entfernt werden.
- User-facing explanation: Der Provider konnte nicht aus der aktiven Konfiguration entfernt werden.
- Suggested action: Aktuellen Stand neu laden und erneut versuchen.
- Suggested action code: reload
- Retryable: yes-after-reload
- UI placement: Provider card and feedback overlay
- Input preservation: Keep the provider visible until deletion succeeds.
- Correlation reference: safe request identifier
- Security considerations: Preserve historical provenance and do not expose internal delete details.
- Backend source: `backend/providers/service.py`, `backend/api/app.py`
- API contract: `docs/api/problem-details-contract.yaml`
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE`
- Required tests: provider API deletion negative tests and frontend delete-failure handling

### `PROVIDER_DELETE_BLOCKED`

- Status: active
- Category: conflict
- Trigger: A provider delete request targets a provider still referenced by queued, running, or cancelling indexing/Cluster-Set work.
- HTTP status: 409
- Problem type: `urn:skm:error:PROVIDER_DELETE_BLOCKED`
- User-facing title: Provider wird noch verwendet.
- User-facing explanation: Der Provider kann erst entfernt werden, wenn aktive Jobs abgeschlossen oder abgebrochen sind.
- Suggested action: Abschluss abwarten oder den aktiven Job abbrechen.
- Suggested action code: wait
- Retryable: yes-after-wait
- UI placement: Provider card and feedback overlay
- Input preservation: Keep the provider visible until deletion succeeds.
- Correlation reference: safe request identifier
- Security considerations: Do not expose project IDs or job IDs from other projects in the conflict response.
- Backend source: `backend/providers/service.py`, `backend/api/app.py`
- API contract: `docs/api/problem-details-contract.yaml`
- Frontend mapping: `frontend/src/App.tsx` `ERROR_MESSAGES_BY_CODE`
- Required tests: provider service/API deletion-blocked tests and frontend delete-failure handling

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
