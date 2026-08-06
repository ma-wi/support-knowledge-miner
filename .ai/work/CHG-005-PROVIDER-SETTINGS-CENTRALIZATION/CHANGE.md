# Incremental change: Provider-Einstellungen zentralisieren

- Change ID: CHG-005-PROVIDER-SETTINGS-CENTRALIZATION
- Status: ready-for-implementation
- Ready for implementation: yes
- Impact analysis accepted: yes
- Requirement: current user request from 2026-08-05
- Work directory: `.ai/work/CHG-005-PROVIDER-SETTINGS-CENTRALIZATION/`
- Decision owner: anfordernder Product Owner
- Last updated: 2026-08-05

## Trigger and problem

Die aktuellen Einstellungen trennen Verbindungskonfiguration, Embedding-Modellfreigabe
und LLM-Modellfreigabe in denselben Provider-Boxen der Tabs „Embedding-Provider“ und
„LLM-Provider“. Dadurch sind OpenAI/Ollama/vLLM visuell und fachlich uneinheitlich:
OpenAI nutzt Checkboxen, Ollama/vLLM teilweise freie Texteingaben, vLLM wird sichtbar
angeboten, und das Feld „OpenAI LLM-Modelle“ dupliziert die neue LLM-Freigabe.

Zusätzlich wird globales Feedback innerhalb der `.content`-Section gerendert. Beim
Ein- und Ausblenden verschiebt sich der Seiteninhalt.

## Current behavior

Aktuelle Besitzer:

- UI-Komposition und globale Feedback-Anzeige: `frontend/src/App.tsx`,
  `frontend/src/App.css`
- Provider-Konfiguration und API: `backend/providers/service.py`,
  `backend/api/app.py`
- Persistenz: `provider_configurations` mit `provider text PRIMARY KEY`

Beobachtbares Verhalten:

- Settings-Tabs: „Embedding-Provider“, „LLM-Provider“, „Nutzer“.
- Provider-Konfigurationen sind pro Basistyp eindeutig (`openai`, `ollama`, `vllm`).
- vLLM wird im Settings-UI angezeigt und ist bei Indizierung auswählbar.
- OpenAI-Embedding-Modelle werden als Checkboxen dargestellt; OpenAI-LLM-Modelle sind
  ein freies Texteingabefeld.
- Ollama-LLM-Modelle sind ein freies Texteingabefeld.
- Ollama-Download ist eine blockierende API-Aktion mit globalem Status; Fortschritt
  ist nicht verfügbar, weil der Backend-Call aktuell `stream:false` verwendet.
- Globale Benachrichtigung ist ein normales Element im Content-Grid.

Canonical specs:

- `docs/specifications/local-runtime-providers.md`
- `docs/specifications/support-knowledge-miner-mvp1.md`

## Desired end state

Design-Zielzustand für die Einstellungen:

- Settings enthält nur noch die Tabs „Provider“ und „Nutzer“.
- Tab „Provider“ zentralisiert Verbindungseinstellungen, API-Key/Secret-Status,
  Anzeigenamen, Hinzufügen/Entfernen und Ollama-Modell-Download.
- Basistypen zum Hinzufügen: OpenAI und Ollama.
- vLLM verschwindet vollständig aus der UI und soll in der Produktionsumsetzung auch
  aus Backend/API/Provider-Runtime entfernt werden. Historische Provenienz darf dabei
  nicht unlesbar werden.
- Provider-Instanzen können mehrfach vorkommen und besitzen einen editierbaren
  Anzeigenamen. Default-Namen sind „OpenAI“ und „Ollama“; weitere Instanzen erhalten
  automatisch eine Nummer, z. B. „OpenAI 2“ oder „Ollama 2“. Der Nutzer darf Namen
  danach frei ändern, auch auf gleiche Anzeigenamen.
- Eine Provider-Instanz wird für Embedding bzw. LLM dadurch bereitgestellt, dass
  Modelle in der jeweiligen Modellfreigabe ausgewählt sind. Separate
  Zweck-Checkboxen entfallen.
- Provider-Boxen verwenden ein einheitliches Layout: Kopf mit Anzeigename/Basistyp,
  Verbindung, Modellfreigaben, Aktionen. Provider-Status-Tags wie
  „API-Key gesetzt“ oder „Verbunden“ werden nicht angezeigt.
- Modellfreigaben für OpenAI und Ollama werden per Checkboxen dargestellt; freie
  Texteingaben für OpenAI-LLM-Modelle werden entfernt. Verfügbare Modelle und
  freigegebene Modelle sind getrennte Zustände, damit abgewählte Modelle sichtbar
  und in ihrer Reihenfolge stabil bleiben.
- Jede Provider-Instanz bietet einen Verbindungstest, der Endpoint/API-Key prüft,
  aber Modellfreigaben nicht verändert.
- „Modelle abrufen“ aktualisiert die verfügbare Modellliste. Nicht mehr beim
  Provider vorhandene Modelle verschwinden aus der verfügbaren Liste und damit auch
  aus aktiven Freigaben; ein fehlgeschlagener Abruf erhält die vorhandenen Listen.
- Bei OpenAI werden in „Embedding-Modelle“ nur Embedding-Modelle angezeigt. In
  „LLM-Modelle“ werden nur `gpt-5*` und höher, `o4-mini`, `gpt-4.1*` und `gpt-4o*`
  angeboten.
- Das OpenAI-API-Key-Feld heißt „OpenAI API-Key“. Bei gespeichertem Key zeigt es
  einen maskierten Placeholder wie „•••••••• gespeichert“, aber keinen echten
  Schlüsselpräfix.
- Jede Provider-Instanz, einschließlich OpenAI, hat eine Entfernen-Aktion.
- Entfernen bedeutet hartes Entfernen aus der aktiven Provider-Konfiguration. Bereits
  erzeugte Import-/Indizierungs-/Cluster-Set-Protokolle behalten Providername,
  Provider-Basistyp und Modell als historische Provenienz, der Provider steht aber
  nicht mehr für erneute Ausführung zur Verfügung.
- Ollama-Modell-Download zeigt mindestens laufenden Status und blockiert einen
  zweiten Download. Status/Fehler sollen aus dem Pull-Ablauf sichtbar werden; wenn
  Fortschritt mit vertretbarem Aufwand verfügbar ist, kann ein Fortschrittsbalken
  angezeigt werden.
- Globale Feedback-Nachrichten erscheinen als Overlay/Popup im bestehenden
  visuellen Stil, reservieren keinen Layoutplatz in `.content`, verschwinden
  automatisch und haben zusätzlich ein „X“ zum manuellen Schließen.

Projekt-Workflow-Zielzustand:

- Beim Start einer Indizierung kann optional eine Provider-Input-Normalisierung
  aktiviert werden: Zeilenumbrüche entfernen oder Zeilenumbruchsgruppen durch ein
  bounded Ersatzzeichen/einen bounded Ersatztext ersetzen sowie optional
  Kleinschreibung für den Provider-Input anwenden. Die Originaltexte bleiben
  unverändert; die Auswahl wird als Indizierungsparameter und Embedding-Metadatum
  protokolliert.
- Importprotokolle zeigen das Importdatum.
- „Logdetails anzeigen“ zeigt nur Validierungsdetails übersprungener/fehlerhafter
  Zeilen. Gibt es keine Details, wird die Aktion nicht angeboten oder klar als nicht
  verfügbar erklärt.
- Beim direkten Öffnen des Explorer-Tabs wird das zuletzt aktualisierte
  abgeschlossene Cluster-Set geladen. „Aktualisiert“ umfasst Neuberechnung und
  Bearbeitung im Explorer.
- Wenn kein Cluster/Cluster-Set verfügbar ist, wird das Explorer-Export-Feld nicht
  angezeigt.
- Indizierung, Cluster-Set-Erstellung, Verfeinerung und
  Ausreißer-Neuberechnung sollen parallel ausführbar sein, soweit die bestehenden
  bounded Worker, Provider-Timeouts und Ressourcenbudgets das zulassen. Die vorher
  geplanten globalen Start-Sperren werden entfernt; Abbruch bleibt möglich.

## Invariants

- OpenAI-Secrets bleiben write-only; gespeicherte Werte werden nicht im Klartext
  angezeigt.
- OpenAI Cloud-Nutzung wird weiterhin erst bei konkreter Datenübertragung explizit
  bestätigt.
- Lokale Provider-Endpunkte bleiben auf erlaubte lokale Hosts beschränkt.
- Keine automatische Provider- oder Modell-Fallback-Auswahl.
- Bisherige Analyse-/Cluster-Provenienz darf durch Umbenennen oder Entfernen von
  Provider-Konfigurationen nicht unverständlich werden.
- Produktionszugriff bleibt ausgeschlossen.

## Scope

### In scope

- Produktionsimplementierung der zentralen Provider-Einstellungen in React/FastAPI.
- Datenbankmigration für mehrere Provider-Instanzen mit stabiler ID,
  Anzeigename, verfügbarer Modellliste, getrennten Embedding-/LLM-Freigaben und
  historischer Provenienz.
- Aktive Entfernung von vLLM aus UI, API-Service-Validierung und Provider-Runtime.
- Feedback-Overlay mit manuellem Schließen und Auto-Ausblenden.
- Ollama-Pull mit einfachem laufend/final erfolgreich/final fehlgeschlagen-Status;
  kein Fortschrittsbalken erforderlich.
- Importprotokoll-Datum und bedingte Logdetails-Aktion.
- Explorer-Default auf zuletzt aktualisiertes abgeschlossenes Cluster-Set und
  verstecktes Export-Feld ohne Cluster.
- Indizierungsformular mit optionaler Zeilenumbruch-Normalisierung nur für den
  Embedding-Provider-Input und optionaler Kleinschreibung für denselben
  Provider-Input.
- Rückbau der projektübergreifenden Start-Sperren für Indizierungs- und
  Cluster-Set-Jobs bei weiterhin bounded lokalen Worker-Queues und erhaltener
  Abbruchmöglichkeit.
- Aktualisierung relevanter Tests, Spezifikationen, Design-Dokumentation und
  Fehlerkatalog-Einträge.

### Out of scope / non-goals

- Prozentgenauer Ollama-Downloadfortschritt.
- Re-Integration von vLLM.
- Änderung der OpenAI-Cloud-Bestätigungspflicht.
- Produktions- oder Remote-Umgebungszugriff.

## Canonical capability specifications affected

- `docs/specifications/local-runtime-providers.md`
- `docs/specifications/support-knowledge-miner-mvp1.md`
- `docs/design/DESIGN_SYSTEM.md`
- `docs/design/COMPONENT_CATALOG.md`

## Existing responsibility decision

- Current owner of the behavior: Provider settings are feature-local UI in
  `frontend/src/App.tsx`; provider storage/API is owned by `backend/providers` and
  `backend/api/app.py`.
- Decision: extend
- Why a new artifact is or is not required: The mockup is a temporary isolated
  design artifact. Future production implementation should extend/rework the
  existing provider responsibility rather than add a second parallel provider system.
- Parallel compatibility behavior, if any: During migration, historical vLLM
  provenance may remain readable, but vLLM must not be selectable or callable in the
  active UI/API after the removal task.
- Removal criterion for retained legacy behavior: Existing single-provider-by-type
  contract can only be replaced after accepted migration/provenance behavior for
  multiple provider instances exists.

## Compatibility, migration, and recovery

- Existing clients or callers: Current UI and backend callers pass `provider` as
  string (`openai`, `ollama`, `vllm`) plus `model`.
- Data migration: Required for real multiple provider instances because
  `provider_configurations.provider` is currently the primary key. Existing
  provider/model provenance must remain readable after hard provider deletion.
- Deployment ordering: Future implementation likely needs compatible API/storage
  expansion before switching frontend selections to provider instance IDs.
- Rollback or recovery: Provider display names and soft deletion/history behavior
  need defined recovery semantics before implementation.
- Deprecation window, if any: none desired for active vLLM support; only historical
  records remain readable.

## Conditional change annexes

## Design classification

- Class: 3
- Highest design class assigned: 3
- Implementation-start design class: 3
- Rationale: New settings information architecture and provider-management flow.
- Existing pattern/components reused: App shell, page tabs, provider cards, model
  checkbox lists, status/feedback styling.
- Applicable design-system rule: Settings/provider grids collapse below `980px`;
  feedback uses `role=status`/`role=alert`; write-only secrets never render saved
  values.
- Existing screens affected: Settings, Indizieren provider/model selection,
  Cluster-Set LLM provider/model selection, Import, Explorer, global feedback.
- Prototype strategy: isolated-prototype
- Visual review required: yes for future production implementation; not required for
  this static draft handoff.
- Required screens: Provider tab, Nutzer tab, Feedback overlay, Ollama download
  state, Import protocols, Explorer empty/default, Indizierung/Cluster-Set running
  states.
- Required states: default, loading/download, disabled download, error, success,
  empty model list, small viewport.
- Required viewports: desktop `1440x1000`, mobile `390x844`.
- DESIGN_DELTA.md required: yes
- Design decision owner, when required: anfordernder Product Owner

### Classification history

| Date | Previous class | New class | Reason | Approved by |
|---|---:|---:|---|---|
| 2026-08-05 | not-applicable | 3 | New Settings IA and provider instance flow | pending |

## Error-and-Recovery Matrix

| Action | Failure | Error code | Safe user message | Placement | Recovery | Retry | Input preservation | Tests | Logging/correlation |
|---|---|---|---|---|---|---|---|---|---|
| Provider speichern | Validation/API failure | `VALIDATION_FAILED` | „Provider-Konfiguration konnte nicht gespeichert werden. Eingaben prüfen und erneut versuchen.“ | Form-level banner in provider card plus overlay summary | Correct input or retry | yes | Preserve safe entered values; never reveal API key | API/service/frontend negative tests | Redacted backend audit/error path |
| Provider prüfen | Local endpoint unavailable / OpenAI auth failure | `VALIDATION_FAILED` | „Verbindung konnte nicht geprüft werden. Endpoint/API-Key prüfen und erneut versuchen.“ | Provider card feedback plus overlay summary | Correct endpoint/key or retry | yes | Preserve endpoint/name/model selection | API/frontend negative tests | Redacted diagnostics only |
| Provider entfernen | Delete fails or active references cannot be snapshotted | `PROVIDER_DELETE_FAILED` | „Provider konnte nicht entfernt werden. Historie bleibt erhalten; bitte erneut versuchen.“ | Provider card + overlay | Retry/reload | yes | No entered settings loss; active config removed only after success | deletion/compatibility tests | Audit hard-delete decision |
| Provider entfernen | Active queued/running/cancelling work still references provider | `PROVIDER_DELETE_BLOCKED` | „Provider wird noch von einer aktiven Berechnung verwendet. Bitte Abschluss abwarten oder den Job abbrechen.“ | Provider card + overlay | Wait/cancel | yes after wait | No entered settings loss; provider remains visible | deletion-blocked service/API tests | Do not expose other-project job identifiers |
| Ollama-Modell herunterladen | Download already running | `PROVIDER_MODEL_PULL_IN_PROGRESS` | „Ein Modell-Download läuft bereits. Bitte Abschluss abwarten.“ | Ollama card download row and overlay | Wait | no until complete | Preserve entered model name | frontend state/API test | No external raw body |
| Ollama-Modell herunterladen | Pull fails/times out | `VALIDATION_FAILED` | „Ollama-Modell konnte nicht geladen werden. Modellname und Verbindung prüfen.“ | Ollama card download row plus overlay error | Retry | yes | Preserve requested model name | API timeout/failure tests | Redacted provider response |

## Acceptance criteria

- [x] AC-1: Static settings mockup exists for the new Provider tab and updated
  single-tab provider settings.
- [x] AC-2: Mockup shows feedback as overlay/popup without content reflow.
- [x] AC-3: Mockup removes vLLM from visible provider choices.
- [x] AC-4: Mockup shows multiple Provider instances with editable names and
  numbered default names.
- [x] AC-5: Mockup shows OpenAI/Ollama model allow-lists as checkbox selections and
  removes „OpenAI LLM-Modelle“ as a free text field.
- [x] AC-6: Mockup shows Ollama download status, disabled second download, and
  optional progress.
- [x] AC-7: Open questions and implementation-impact notes are documented.
- [x] AC-8: Separate mockup covers Import date/logdetails, Explorer empty/default
  loading and single-running-job constraints.
- [ ] AC-9: Production settings UI contains only Provider and Nutzer tabs and
  supports add/update/delete for OpenAI/Ollama provider instances.
- [ ] AC-10: Backend and database support multiple provider instances while keeping
  historical analysis/cluster provenance readable after hard provider deletion.
- [ ] AC-11: vLLM is absent from active UI/API provider choices and provider runtime.
- [ ] AC-12: Ollama model pull blocks a second pull while running and returns safe
  final success/failure status.
- [ ] AC-13: Import protocol dates/details and Explorer default/export visibility are
  implemented.
- [ ] AC-14: Indizierung, Cluster-Set-Erstellung, Verfeinerung und
  Ausreißer-Neuberechnung können innerhalb der bounded lokalen Worker parallel
  gestartet werden; die vorherigen globalen Start-Sperren sind aus Backend und UI
  entfernt.

## Open questions and blockers

Keine produktionsblockierenden offenen Fragen.

Accepted decisions:

- Anzeigenamen sind nicht eindeutig; technische Identität ist die Provider-Instanz-ID.
- Neue Default-Namen werden typweise nummeriert, können danach aber frei geändert
  werden.
- Provider werden hart aus der aktiven Konfiguration gelöscht; historische
  Analyse-/Cluster-Provenienz bleibt als Snapshot lesbar.
- vLLM wird aus aktiver UI/API/Runtime entfernt.
- Ollama-Pull verwendet die einfache Statusvariante: laufend, final erfolgreich oder
  final fehlgeschlagen. Polling/Backend-Jobstatus reicht; kein Prozentfortschritt.
- Explorer verwendet `cluster_sets.updated_at`; Explorer-Bearbeitungen müssen dieses
  Feld am owning Cluster-Set aktualisieren.

## Readiness decision

- Shared understanding confirmed: yes
- Confirmed by: user message on 2026-08-05
- Confirmation date: 2026-08-05
- Impact analysis accepted: no
- Ready for implementation: no
- Remaining blockers: Produktionsimplementierung benötigt aktualisierte
  Spezifikation, Datenmodell-/API-Plan und Tests.
