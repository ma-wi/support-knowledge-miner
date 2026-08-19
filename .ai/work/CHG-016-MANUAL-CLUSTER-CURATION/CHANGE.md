# Incremental change: Manuelle Cluster-Kuration und direkte Explorer-Bearbeitung

- Change ID: CHG-016-MANUAL-CLUSTER-CURATION
- Status: awaiting-confirmation
- Requirement: `docs/requirements/chg-016-manual-cluster-curation.md`
- Work directory: `.ai/work/CHG-016-MANUAL-CLUSTER-CURATION/`
- Decision owner: mawi
- Last updated: 2026-08-19

## Trigger and problem

Der bestehende Explorer korrigiert nur vorhandene Cluster-Metadaten. Fehlende
Cluster, direkte FAQ-Korrekturen und einzelne Quellenverschiebungen in die
Ausreißer sind nicht möglich.

## Current behavior

`frontend/src/App.tsx` rendert vorhandene Cluster als Tabelle, speichert Titel,
Kategorie und Status über `PATCH /api/projects/{project_id}/clusters/{cluster_id}`
und lädt Quellen paginiert über den bestehenden Source-Endpunkt. FAQ-Felder sind
nur `auto_summary_question` und `auto_summary_answer`. `backend/clusters/service.py`
führt Cluster-Set-Erzeugung, Child-Lineage, Memberships und manuelle Clusterfelder.
`cluster_memberships` erzwingt pro Cluster-Set genau eine Zuordnung je Paar.
Die Spezifikation verlangt, dass strukturelle Operationen neue Child-Sets erzeugen.

Canonical state: `docs/specifications/support-knowledge-miner-mvp1.md`, Abschnitte
„Cluster-Sets“, „Cluster Explorer“ und „Exclusion, outlier management and refinement“.

## Desired end state

Der bestehende Cluster-/Cluster-Set-Service wird um einen fachlich begrenzten
manuellen Kurationpfad erweitert. Ein leerer oder beispielbasierter Cluster entsteht
als `manual_edit`-Child. Beispielbasierte Felder werden durch ein strukturiertes,
bounded LLM-Ergebnis initialisiert; Treffer werden über vorhandene Embeddings
ermittelt, angezeigt und nach Bestätigung manuell zugeordnet. Ein dedizierter
manueller Child-Zustand kann nach D001 mehrfach kuratiert werden.

Der bestehende Cluster-PATCH-Vertrag erhält manuelle FAQ-Overrides. Inline-Textfelder
speichern auf Blur/Commit, der Status speichert auf Auswahländerung. Der Source-Dialog
erhält eine Verschiebeaktion, die Membership atomar in einen Ausreißer-Cluster überführt.
Ein einzelner Cluster kann über den bestehenden Summary-Providerpfad neu beschrieben
werden, ohne Memberships oder andere Cluster zu verändern. Der Source-Dialog kann
eine oder mehrere Quellen als Referenzen an eine bereichsbezogene Suche übergeben;
deren Ergebnisse bleiben zunächst Vorschau und Selektion.

## Invariants

- Automatisch erzeugte Cluster-Sets und ihre Memberships bleiben unverändert.
- Pro Cluster-Set und Nachrichtenpaar existiert höchstens genau eine Membership.
- Jede manuelle Zuordnung ist als `assignment_type = manual` und mit bounded Metadata
  nachvollziehbar.
- Alle Operationen bleiben projektbezogen autorisiert und transaktional.
- Rohsupporttexte, Prompts, Providerantworten und vollständige ID-Listen erscheinen
  nicht in Logs, Fehlerdetails oder Telemetrie.
- Bestehende API-Felder und automatische Summary-Felder bleiben kompatibel.
- Ausreißer sind nicht gelöscht; sie bleiben im geladenen manuellen Zustand sichtbar.
- Failed writes rollen Optimistic Updates zurück und erzeugen keine Erfolgsmeldung.
- Eine Einzel-Cluster-Summary ändert keine Memberships, Cluster-Nachbarn oder
  Cluster-Set-Struktur.
- Eine Referenzsuche verändert keine Daten, bevor ein manueller Commit bestätigt wird.

## Scope

### In scope

- Leeres manuelles Cluster mit vier Pflichtfeldern.
- Beispielbasierter LLM-Start und semantische Treffer-Vorschau.
- Einzel-Cluster-LLM-Aktualisierung.
- Referenzauswahl und Ähnlichkeitssuche aus dem Quellen-Dialog.
- Trefferzuordnung in ein neues manuelles Cluster.
- Inline-Autosave für fünf bestehende Clusterfelder.
- Einzelnes Verschieben von Quellen in Outliers.
- Migration, API-/Frontend-Fehlervertrag, Tests, Spezifikation und UI-Evidenz.

### Out of scope / non-goals

- Neue Kandidaten- oder Export-Pipeline.
- Externe Fuzzy-Matching-Abhängigkeit.
- Automatische FAQ-Freigabe oder Kundenkommunikation.
- Freie Membership-Bearbeitung automatisch erzeugter Sets.

## Canonical capability specifications affected

- `docs/specifications/support-knowledge-miner-mvp1.md` — in place aktualisieren.

## Existing responsibility decision

- Current owner: `backend/clusters/service.py` für Cluster-Set/Membership-Logik,
  `backend/api/app.py` für Problem Details und Verträge, `frontend/src/App.tsx`
  für Explorer-Interaktion, `backend/analysis/service.py`/Provider-Service für
  Embeddings und LLM-Provider.
- Decision: extend.
- Why no parallel artifact: `manual_edit`, `cluster_memberships`, bestehender
  Cluster-PATCH, Source-Dialog und Provider-/Summary-Pfade decken die Verantwortung
  bereits ab. Eine zweite Cluster- oder Membership-Implementierung wäre inkonsistent.
- Compatibility behavior: bestehende PATCH-/GET-Felder bleiben; neue Felder sind
  optional und unbekannte API-Felder werden weiterhin ignoriert.
- Removal criterion: Keine parallele Übergangspipeline; neue Endpunkte werden nach
  vollständiger UI-Migration der bestehenden Owner direkt genutzt.

## Compatibility, migration, and recovery

- Existing clients: alte Clients sehen weiterhin automatische Summary-Felder und
  können alte PATCH-Payloads senden.
- Data migration: neue nullable manuelle FAQ-Spalten und ggf. ein bounded
  Manual-Edit-Lifecycle-/Versionfeld; keine Umschreibung bestehender Memberships.
- Deployment ordering: Migration vor Backend; Backend-Vertrag vor Frontend-Nutzung;
  Spezifikation/Fehlerkatalog im selben Change.
- Rollback/recovery: neue manuelle Child-Sets können als lokale Historienknoten
  gelöscht werden; Eltern bleiben unverändert. Bei Konflikt wird nicht überschrieben.
- Deprecation window: none; alte Felder bleiben kompatibel.

## Design classification

- Class: 2
- Highest design class assigned: 2
- Implementation-start design class: not-started
- Rationale: Neuer mehrstufiger Erstellungs-/Vorschaufluss und neue Dialogaktionen;
  Inline-Autosave nutzt bestehende Tabellen-/Dialogmuster.
- Design artifact: `.ai/work/CHG-016-MANUAL-CLUSTER-CURATION/DESIGN_DELTA.md`
- Design approval: pending

## Security assurance

- Required: ja — Supporttexte, LLM-Netzwerkgrenze, projektbezogene APIs,
  untrusted LLM-Ausgaben, Ressourcenlimits und irreversible Membership-Änderungen.
- Threat model: `.ai/work/CHG-016-MANUAL-CLUSTER-CURATION/THREAT_MODEL.md`
- Specialist review: erforderlich für Datenfreigabe an Provider, Autorisierung,
  bounded Similarity-/LLM-Verarbeitung und transaktionale Membership-Änderung.

## Error behavior impact

### Actions covered

- Create: leeres oder beispielbasiertes manuelles Cluster.
- Search: Ähnlichkeitssuche/Vorschau.
- Update: Inline-Felder und Status.
- Delete/move: Quelle in Outliers verschieben.
- Load/recovery: Cluster, Quellen und neuer Child-Zustand.

### Proposed new or changed codes

- `CLUSTER_MANUAL_CREATE_INVALID`
- `CLUSTER_MANUAL_EXAMPLES_REQUIRED`
- `CLUSTER_MANUAL_SUMMARY_FAILED`
- `CLUSTER_MANUAL_MATCH_FAILED`
- `CLUSTER_MANUAL_MATCH_EMPTY`
- `CLUSTER_MANUAL_EDIT_CONFLICT`
- `CLUSTER_MANUAL_SOURCE_MOVE_FAILED`
- `CLUSTER_SINGLE_SUMMARY_FAILED`
- `CLUSTER_REFERENCE_SELECTION_INVALID`
- `CLUSTER_REFERENCE_SEARCH_FAILED`
- `CLUSTER_REFERENCE_SEARCH_EMPTY`

### Error-and-Recovery Matrix

| Action | Failure | Error code | Safe user message | Placement | Recovery | Retry | Input preservation | Negative tests | Logging/correlation |
|---|---|---|---|---|---|---|---|---|---|
| Empty cluster create | Pflichtfeld fehlt/ungültig | `CLUSTER_MANUAL_CREATE_INVALID` | Titel, Kategorie und beide FAQ-Felder müssen ausgefüllt werden. | inline/Formbanner | Eingaben korrigieren | yes | alle sicheren Felder | API + UI | Request-ID, keine Texte |
| Example cluster create | kein Beispiel | `CLUSTER_MANUAL_EXAMPLES_REQUIRED` | Mindestens ein Beispiel ist erforderlich. | Eingabefeld/Formbanner | Beispiel ergänzen | yes | Beispiele behalten | API + UI | nur Aggregat |
| LLM summary | Provider, Bestätigung, Timeout oder Schemafehler | `CLUSTER_MANUAL_SUMMARY_FAILED` | Die Felder konnten aus den Beispielen nicht erstellt werden. Provider prüfen oder manuell fortfahren. | Formbanner | Provider prüfen/manuell wechseln | yes | Beispiele/Scope behalten | Provider/Schema/timeout | keine Prompts/Antworten |
| Similarity preview | Embedding/Scope/Budgetfehler | `CLUSTER_MANUAL_MATCH_FAILED` | Ähnliche Nachrichten konnten nicht gesucht werden. | Preview-Bereich | Eingabe/Scope reduzieren oder erneut versuchen | yes | Eingabe und Filter behalten | API + resource bounds | IDs nur aggregiert |
| Similarity preview | keine Treffer | `CLUSTER_MANUAL_MATCH_EMPTY` | Es wurden keine passenden Nachrichten gefunden. | Preview-Bereich | Schwelle/Basis anpassen | yes | Eingabe behalten | no-results | Aggregat |
| Inline update | invalid/not found/conflict/network | `CLUSTER_MANUAL_EDIT_CONFLICT` oder bestehender Validierungscode | Die Änderung wurde nicht gespeichert; der vorherige Wert bleibt erhalten. | Tabellenzelle + status | Wert korrigieren oder neu laden | yes | Wert/Filter behalten | rollback/no-success | Request-ID |
| Source move | Set/Paar/Outlier-Transaktion nicht verfügbar | `CLUSTER_MANUAL_SOURCE_MOVE_FAILED` | Die Quelle konnte nicht in die Ausreißer verschoben werden. | Source-Dialog | Dialogzustand behalten, erneut versuchen/neuladen | yes | Quellenliste behalten | auth/not-found/conflict/rollback | IDs nicht vollständig |
| Single-cluster LLM refresh | Provider, Sample, Timeout oder Schemafehler | `CLUSTER_SINGLE_SUMMARY_FAILED` | Die Cluster-Zusammenfassung konnte nicht aktualisiert werden. | Cluster-Zeile/Formbanner | Provider prüfen oder erneut versuchen | yes | Explorer/Clusterwerte behalten | Provider/schema/timeout/no-success | keine Prompts/Antworten |
| Reference selection | keine gültige Quelle/Basis/Bereich | `CLUSTER_REFERENCE_SELECTION_INVALID` | Die Referenzauswahl ist für diese Suche ungültig. | Source-Dialog/Preview | Auswahl oder Suchbasis korrigieren | yes | Auswahl behalten | API + UI | nur Aggregat |
| Reference search | Embedding, Bereich oder Provider fehlerhaft | `CLUSTER_REFERENCE_SEARCH_FAILED` | Ähnliche Nachrichten konnten nicht gesucht werden. | Preview-Bereich | Bereich/Basis anpassen oder erneut versuchen | yes | Auswahl/Filter behalten | bounds/provider/network | keine Rohtexte/kompletten IDs |
| Reference search | keine Treffer | `CLUSTER_REFERENCE_SEARCH_EMPTY` | Es wurden keine ähnlichen Nachrichten gefunden. | Preview-Bereich | Bereich oder Suchbasis ändern | yes | Auswahl behalten | no-results | Aggregat |
| Unknown | unerwarteter Fehler | `UNEXPECTED_ERROR` | Die Aktion konnte nicht abgeschlossen werden. Bitte erneut versuchen oder neu laden. | betroffener Bereich | retry/reload | yes | safe state | unknown-code | sichere Korrelation |

## Acceptance criteria

- [ ] Kriterien aus `docs/requirements/chg-016-manual-cluster-curation.md` sind
  nach D001–D011-Bestätigung vollständig testbar.

## Readiness decision

- Shared understanding confirmed: no
- Confirmed by:
- Confirmation date:
- Impact analysis accepted: no
- Ready for implementation: no
- Remaining blockers: D001–D011, Design-Delta-Approval und konkrete API-/Migration-
  Verträge im Readiness-Review.
