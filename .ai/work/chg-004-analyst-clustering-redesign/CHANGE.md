# Incremental change: Analystenorientierte Indizierungs- und Clusteranalyse

- Change ID: CHG-004
- Status: ready-for-implementation
- Requirement: `docs/requirements/chg-004-analyst-clustering-redesign.md`
- Work directory: `.ai/work/chg-004-analyst-clustering-redesign/`
- Decision owner: anfordernder Product Owner
- Last updated: 2026-08-04

## Trigger and problem

Die alte Umsetzung vermischt Analyseprofile, Runs, Embeddings, Clustering,
Kandidaten und Export. Der genehmigte Analystenworkflow braucht stattdessen
Import → Indizieren → Cluster-Sets → Explorer.

## Current behavior

- Provider/Profile: `backend/providers/service.py`,
  `/api/projects/{project_id}/analysis-profiles`, Project-Tab „Profile“.
- Runs/Embeddings: `backend/analysis/service.py`,
  `/api/projects/{project_id}/analysis-runs`, Project-Tab „Runs“.
- Clustering: `backend/clusters/service.py`, run-gebundene Cluster.
- Kandidaten/Export: `backend/candidates/service.py`, Project-Tab „Kandidaten“,
  alter Candidate-Export.
- Canonical docs before this change: MVP spec and ADR-0003 encoded profiles.

## Desired end state

- Analyseprofile werden ohne Kompatibilität entfernt.
- Indizierungen erzeugen `message`- und `answer`-Embeddings.
- Cluster-Sets sind persistierte finale Analyseartefakte mit Parametern,
  LLM-Provenienz, Parent/Child-Lineage und Quellen-Snapshot.
- Einstellungen trennen Embedding-Provider und LLM-Provider.
- Explorer ist tabellarisch, quellenprüfbar, verfeinerbar und exportiert den
  aktuellen Filterstand als CSV/JSON über einen eigenen Export-Abschnitt.
- Der eigenständige Kandidatenworkflow entfällt.

## Invariants

- Kein Produktionszugriff.
- Projektisolierung bleibt zwingend.
- Originaltexte und Secrets bleiben geschützt.
- OpenAI-Texttransfer braucht konkrete Bestätigung.
- Lokale Provider-Endpunkte bleiben allow-listed.
- Clustering baut keine vollständige paarweise Distanzmatrix.
- Strukturänderungen überschreiben keine Cluster-Sets.

## Scope

### In scope

- Profil/Runs → Indizierung/Cluster-Sets.
- LLM-Provider.
- Explorer-Tabelle, Quellen-Dialog, Ausreißer-Box, Export-Abschnitt.
- Lokale Migration ohne Profil-Kompatibilität.
- Tests, Specs, ADR, Design- und Error-Readiness.

### Out of scope / non-goals

- SaaS/Produktion/Live-Integrationen.
- Automatische finale Wissensartikel-Freigabe.
- Rückwärtskompatibilität für Analyseprofile.

## Canonical capability specifications affected

- `docs/specifications/support-knowledge-miner-mvp1.md`
- `docs/specifications/local-runtime-providers.md`

## Existing responsibility decision

- Existing owner: provider/profile service, analysis service, cluster service,
  candidate service, project tabs and MVP spec.
- Decision: replace/split responsibility.
- New artifact justification: `ClusterSet` is required because run-bound clusters
  cannot represent multiple saved parameter variants or hierarchy.
- Compatibility: none for profiles; local derived old data may be dropped.

## Compatibility, migration, and recovery

- Retain projects, users, provider configurations, imports and dataset versions.
- Old profiles, runs, embeddings, clusters and candidates may be dropped by local
  migration.
- Require a human-facing local backup note before destructive migration.

## Error behavior impact

- New/changed actions: project/import/indexing/cluster-set/explorer/export actions
  listed in the matrix below.
- Removed actions: create/edit profile, start run from profile, Kandidaten tab,
  separate Export tab, old candidate curation/export.
- Catalog: `docs/errors/ERROR_CATALOG.md` declares active CHG-004 codes.
- Input preservation: selections, parameters, filters and typed names are preserved
  where safe.
- Logging/correlation: redacted job/request identifiers only.

## Error-and-Recovery Matrix

| Action | Failure | Error code | Safe user message | Placement | Recovery | Retry | Input preservation | Tests | Logging |
|---|---|---|---|---|---|---|---|---|---|
| Indizierung starten | Modell fehlt | INDEXING_MODEL_UNAVAILABLE | Das gewählte Embedding-Modell ist nicht verfügbar. | Indizierungsformular | Modell wechseln | yes | form fields | API/UI | job/request id |
| Indizierung starten | OpenAI nicht bestätigt | INDEXING_CLOUD_CONFIRMATION_REQUIRED | Diese Indizierung würde Originaltexte an OpenAI senden. | Indizierungsformular | bestätigen oder lokal wählen | yes | form fields | API/UI | no text |
| Indizierung abbrechen | nicht abbrechbar | INDEXING_CANCEL_NOT_AVAILABLE | Diese Indizierung kann nicht mehr abgebrochen werden. | Indizierungskarte | Liste aktualisieren | yes | list | API/UI | job id |
| Cluster-Set erzeugen | Indizierung nicht fertig | INDEXING_NOT_COMPLETE | Diese Indizierung ist noch nicht abgeschlossen. | Cluster-Set-Formular | fertige Indizierung wählen | yes | parameters | API/UI | no writes |
| Cluster-Set erzeugen | Vektorbasis fehlt | CLUSTER_VECTOR_BASIS_UNAVAILABLE | Die gewählte Vektorbasis ist nicht verfügbar. | Cluster-Set-Formular | Basis wechseln | yes | parameters | service/UI | no writes |
| Cluster-Set erzeugen | Beispielanzahl ungültig | CLUSTER_SUMMARY_SAMPLE_COUNT_INVALID | Die Anzahl der LLM-Beispiele muss mindestens 1 sein. | Cluster-Set-Formular | Zahl korrigieren | yes | form fields | service/UI | no provider call |
| Cluster-Set erzeugen | Clusterbudget überschritten | CLUSTER_BUDGET_EXCEEDED | Die Clusterung ist für die aktuelle Datenmenge zu groß. | Cluster-Set-Formular | Umfang reduzieren | yes | form fields | service/UI | capacity only |
| Cluster-Set erzeugen | OpenAI-LLM nicht bestätigt | LLM_CLOUD_CONFIRMATION_REQUIRED | Diese Zusammenfassung würde Originaltexte an OpenAI senden. | Cluster-Set-Formular | bestätigen oder lokal wählen | yes | form fields | API/UI | no text |
| Cluster-Set erzeugen | LLM nicht erreichbar | LLM_PROVIDER_UNAVAILABLE | Das LLM konnte nicht erreicht werden. | Cluster-Set-Status | Provider prüfen | yes | result/params | service/UI | redacted |
| Cluster-Set erzeugen | LLM-Ausgabe ungültig | CLUSTER_SUMMARY_FAILED | Die Zusammenfassung konnte nicht sicher erzeugt werden. | Cluster-Set-Status | erneut versuchen | yes | cluster result | service/UI | no raw body |
| Cluster-Set abbrechen | nicht abbrechbar | CLUSTER_SET_CANCEL_NOT_AVAILABLE | Dieses Cluster-Set kann nicht mehr abgebrochen werden. | Cluster-Set-Karte | Liste aktualisieren | yes | tree | API/UI | job id |
| Cluster-Set laden/löschen | nicht gefunden | CLUSTER_SET_NOT_FOUND | Das Cluster-Set wurde nicht gefunden. | Explorer/Baum | Liste neu laden | yes | filters | API/UI | redacted |
| Quellen öffnen | Clusterquelle fehlt | CLUSTER_SOURCE_NOT_FOUND | Die Quellen dieses Clusters konnten nicht geladen werden. | Quellen-Dialog | Set neu laden | yes | filters | API/UI | scoped |
| Verfeinern | keine Quellen | CLUSTER_REFINEMENT_EMPTY_SOURCE | Für die Verfeinerung sind keine Quellen ausgewählt. | Refinement panel | Cluster einschließen | yes | parameters | service/UI | no writes |
| Import löschen | abhängig genutzt | IMPORT_IN_USE_DELETED | Der Datensatz wird gelöscht; abhängige Artefakte bleiben erhalten. | Importübersicht | bestätigen/abbrechen | no | list | API/UI | audit |
| Indizierung löschen | abhängig genutzt | INDEXING_RUN_DELETED | Die Indizierung wird gelöscht; abhängige Cluster-Sets bleiben erhalten. | Indizierungsübersicht | bestätigen/abbrechen | no | list | API/UI | audit |
| Explorer suchen | keine Treffer | CLUSTER_SEARCH_NO_RESULTS | Keine Cluster entsprechen der Textsuche. | Explorer-Tabelle | Filter ändern | yes | search/filter | UI | no text |
| Explorer exportieren | keine Zeilen | EXPLORER_EXPORT_EMPTY | Es gibt keine exportierbaren Zeilen im aktuellen Filterstand. | Export-Abschnitt | Filter ändern | yes | search/filter | API/UI | no file |
| Explorer exportieren | Exportfehler | EXPLORER_EXPORT_FAILED | Der Export konnte nicht erstellt werden. | Export-Abschnitt | retry/Format wechseln | yes | search/filter | API/UI | redacted |
| Namen speichern | Autosave schlägt fehl | DISPLAY_NAME_SAVE_FAILED | Der Name konnte nicht gespeichert werden. | Namensfeld | erneut versuchen | yes | typed name | API/UI | resource id |
| Ausreißer ausschließen | keine Quellen übrig | CLUSTER_OUTLIER_EMPTY_RESULT | Mit diesem Threshold bleiben keine auswertbaren Quellen übrig. | Ausreißer-Box | Threshold reduzieren | yes | parameters | service/UI | no write |
| Ausreißer ausschließen | Berechnung fehlschlägt | CLUSTER_OUTLIER_RECALCULATION_FAILED | Der Ausreißer-Ausschluss konnte nicht abgeschlossen werden. | Ausreißer-Box | Parameter prüfen | yes | parameters | service/UI | redacted |
| Historie laden | Lineage nicht verfügbar | CLUSTER_SET_LINEAGE_UNAVAILABLE | Die Herkunft dieses Cluster-Sets konnte nicht geladen werden. | Baum/Analysepfad | erneut laden | yes | loaded set | API/UI | no text |

## Design classification

- Design class: 3
- Highest design class assigned: 3
- Implementation-start design class: 3
- Class: 3
- Rationale: neue Informationsarchitektur, Projekt-Navigation, Workflow-Namen und
  spätere table-first Explorer-Komposition.
- Existing pattern/components reused: existing sidebar, tabs, panels, forms, buttons
  and status styling as production baseline.
- Applicable design-system rule: `docs/design/DESIGN_SYSTEM.md` existing shell,
  panel, form, feedback and responsive rules extended by `DESIGN_DELTA.md`.
- Existing screens affected: project workspace tabs, settings provider tabs,
  import/indexing views, future cluster-set and explorer views.
- Prototype strategy: isolated-prototype
- Visual review required: yes
- Required screens: see `DESIGN_DELTA.md`.
- Required states: see `DESIGN_DELTA.md`.
- Required viewports: desktop 1440x1000 and mobile 390x844.
- DESIGN_DELTA.md required: yes
- Design decision owner, when required: anfordernder Product Owner

## Acceptance criteria

- [x] AC-1: Decision Owner bestätigt Change Request und Mockup-Flow.
- [x] AC-2: Produktentscheidungen sind entschieden.
- [x] AC-3: Impact, Design, Ziel-Spezifikation und Plan sind ready.

## Open questions and blockers

- Keine offenen Produktentscheidungen.
- T2 ist bereit; spätere Tasks erhalten eigene Work Items vor Umsetzung.

## Readiness decision

- Shared understanding confirmed: yes
- Confirmed by: anfordernder Product Owner
- Confirmation date: 2026-08-04
- Impact analysis accepted: yes
- Ready for implementation: yes
- Remaining blockers: keine für T2; spätere Tasks brauchen eigene Work Items
