# Design Delta

## Metadata

- Change ID: CHG-004
- Design class: 3
- Highest design class assigned: 3
- Implementation-start design class: 3
- Status: approved
- Affected capability specifications: `docs/specifications/support-knowledge-miner-mvp1.md`, `docs/specifications/local-runtime-providers.md`
- Existing screens affected: project overview/sidebar, project workspace tabs,
  import, indexing, settings provider tabs, cluster-set overview and explorer.
- Prototype strategy: isolated-prototype
- Prototype artifact type: clickable-html-prototype
- Prototype artifact or revision: `.ai/work/chg-004-analyst-clustering-redesign/prototype`
- Change base revision: 5134180bce33e1d34653285590105efb27c17a36
- Required visual gates: browser evidence and independent visual review after
  production implementation for desktop 1440x1000 and mobile 390x844.
- Decision owner: anfordernder Product Owner
- Last updated: 2026-08-04

## Classification history

| Date | Previous class | New class | Reason | Approved by |
|---|---:|---:|---|---|
| 2026-08-04 | 0 | 3 | Neue Informationsarchitektur, Navigation, Workflow-Namen, table-first Explorer und responsive Interaktionsrichtung. | anfordernder Product Owner |

## Problem and user outcome

Der bisherige UI- und Domänenfluss bündelt Analyseprofile, Runs, Clustering,
Kandidaten und Export in einem für Analysten unklaren Arbeitsmodell. Der Nutzer
soll stattdessen direkt Import → Indizieren → Cluster-Sets → Explorer durchlaufen
und gespeicherte Analysevarianten nachvollziehbar vergleichen.

## Current experience

Die Projektansicht enthält Profile, Runs, Cluster Explorer, Kandidaten und Export
als getrennte primäre Tabs. Runs hängen fachlich an Analyseprofilen und erzeugen
nur die bisherige Embedding-Sicht. Cluster werden kartenbasiert gezeigt; Quellen
sind nicht als fokussierter Dialog angelegt.

## Desired experience

Die Hauptnavigation zeigt Projekte und Einstellungen. Ein Projekt verwendet die
Tabs Import, Indizieren, Cluster-Sets, Explorer und Projekt löschen. Indizierungen
werden als eigene Jobs mit Fortschritt angezeigt. Cluster-Sets werden später als
persistierte Analysevarianten geladen und im Explorer tabellarisch geprüft.

## User flow

1. Nutzer öffnet die Projektübersicht, erstellt oder öffnet ein Projekt.
2. Nutzer importiert oder benennt Dataset-Versionen im Import-Tab.
3. Nutzer startet im Tab Indizieren eine Indizierung aus Dataset,
   Embedding-Provider und Modell.
4. Nutzer verfolgt Status, Prozentfortschritt und Phase in der Indizierungsliste
   und kann laufende Jobs abbrechen.
5. Nach Abschluss nutzt der Nutzer eine fertige Indizierung als Basis für spätere
   Cluster-Sets.

## Screen inventory

| Screen or state | Existing | Changed | New | Notes |
|---|---:|---:|---:|---|
| Projektübersicht und Sidebar | yes | yes | no | Projekte öffnen Übersicht; geöffnete Projekte erscheinen als Unterpunkte. |
| Project workspace tabs | yes | yes | no | Profile/Runs/Kandidaten werden durch Import/Indizieren/Cluster-Sets/Explorer ersetzt. |
| Import overview | yes | yes | no | Anzeigenamen und Löschsemantik werden sichtbar. |
| Indizieren | partial | yes | no | Ersetzt aktiven Runs/Profile-Start mit profilfreier Jobliste. |
| Cluster-Sets | no | no | yes | Umsetzung nach T2. |
| Explorer table and source dialog | partial | yes | yes | Umsetzung nach T2. |
| Settings provider tabs | yes | yes | no | Embedding-Provider und LLM-Provider werden getrennt. |

## State inventory

- default: Projekt- und Tab-Inhalte zeigen die nächste fachliche Aktion.
- loading: Ladezustände bleiben im jeweiligen Panel oder in der betroffenen Liste.
- empty: keine Projekte, keine Imports, keine Indizierungen, keine Cluster-Sets und
  keine Explorer-Zeilen haben eigene Empty States.
- error: Primärfehler stehen am handlungsfähigen Ort, nicht nur im Overlay.
- validation: Formularvalidierung zeigt Feld- oder Formularfehler mit erhaltener
  Eingabe.
- disabled: Lade-/Weiterverwendungsaktionen sind deaktiviert, bis der relevante Job
  `fertig` ist.
- submitting: Start-, Abbruch-, Lösch- und Umbenennungsaktionen beenden ihren
  Pending-Zustand auch bei Fehlern.
- success: Erfolgsfeedback erscheint nicht nach fehlgeschlagenen Aktionen.
- long content: Tabellen/Dialoge müssen lange Texte begrenzen oder scrollen.
- small viewport: Kontrollen stehen oberhalb der Inhalte; Tabellen/Dialoge bleiben
  bedienbar.
- permission restricted: nicht relevant für differenzierte Rollen; Authentifizierung
  bleibt Voraussetzung für geschützte Projektaktionen.
- partial data: gelöschte Datensätze oder Indizierungen werden als gelöschte Basis
  markiert, abhängige Artefakte bleiben verständlich.

## Responsive behavior

Desktop nutzt eine arbeitsflächenorientierte Zweispalten- oder Panel-Komposition.
Mobile stapelt Formulare, Listen und sekundäre Panels; breite Tabellen werden
horizontal scrollbar oder später funktionsgleich verdichtet.

## Component impact

### Existing components reused

- Sidebar-, Tab-, Panel-, Formular-, Button-, Status- und Feedback-Styles aus der
  bestehenden React-Anwendung bleiben die Produktionsbasis.

### Existing components extended

- Projekt-Tabs werden fachlich umbenannt und neu zusammengesetzt.
- Provider-/Modell-Auswahl wird für Indizierungen genutzt.
- Feedback und Fehlerplatzierung werden code-aware ergänzt.

### New shared components

| Name/responsibility | Target path/layer | API/variants/states | Tests | Accessibility | Story/equivalent | Catalog entry |
|---|---|---|---|---|---|---|
| none | not-applicable | not-applicable | not-applicable | not-applicable | not-applicable | not-applicable |

### New feature-local components

- Indizierungsformular und Indizierungsliste innerhalb der Projektansicht.
- Spätere Cluster-Set-Baumansicht, Explorer-Tabelle und Quellen-Dialog.

### Components replaced or removed

- Aktive Profile-Form-/Listenkomposition.
- Runs-Tab-Benennung und Profil-Startauswahl.
- Später Kandidaten- und separater Export-Tab.

### Rejected reuse options

- Profilformular-State wird nicht wiederverwendet, weil er entfernte
  Analyseprofilfelder konservieren würde.
- Clusterkarten werden nicht als Explorer-Hauptansicht verwendet, weil sie dichte
  Analyse und Vergleichbarkeit nicht tragen.

### Rationale

Die Änderung braucht neue fachliche Zusammensetzung, aber keine neue
Design-System-Komponentenfamilie für T2.

## Design-system impact

- docs/design/DESIGN_SYSTEM.md impact: aktuelle Regeln müssen die neue
  Projekt-/Analyse-Informationsarchitektur, Status-Chips mit Prozenten,
  Job-Listenplatzierung und primäre Fehlerplatzierung abbilden.
- docs/design/COMPONENT_CATALOG.md impact: Katalog muss die wiederverwendeten
  Shell-/Panel-/Feedback-Patterns und neue feature-lokale Indizierungsbestandteile
  verorten.
- Tokens: bestehende Farb-, Abstand-, Schrift- und Status-Tokens bleiben Grundlage;
  neue Zustände müssen vorhandene Status-/Feedback-Tokens nutzen.
- Accessibility: Tabs bleiben Tastaturbedienbar; Status nutzt `role="status"`,
  Fehler `role="alert"`; spätere Dialoge brauchen Fokusführung.
- Responsive behavior: Desktop-Panels und mobile Stapelung sind verbindliche
  Umsetzungsrichtung.
- Existing-screen/component migration: Profile/Runs/Kandidaten-/Export-Primärtabs
  werden schrittweise aus aktiven Workflows ersetzt statt parallel erweitert.
- Project-wide visual-regression impact: geänderte Navigation, Projektansicht,
  Indizieren, Einstellungen und spätere Explorer-Screens brauchen neue
  revision-bound Browser-Evidence.

## Accessibility requirements

- Tabs bleiben per Tastatur nutzbar und semantisch als Navigation erkennbar.
- Status- und Fehlertexte unterscheiden `role="status"` und `role="alert"`.
- Job-Abbruch- und Löschaktionen haben klare Namen und behalten Fokus/Erholung bei
  Fehlern.
- Spätere Tabellen nutzen echte Tabellensemantik; spätere Dialoge trapen Fokus,
  schließen per Escape/Button und geben Fokus zurück.

## Error experience

Primäre Fehler erscheinen dort, wo der Nutzer handeln kann: Formularfehler im
aktuellen Formular, Jobfehler auf der betroffenen Karte, Tabellen-/Dialogfehler im
Explorer und Exportfehler im Export-Abschnitt. Das nicht-blockierende Overlay ist
nur ergänzendes Feedback.

### Action and failure inventory

| Action | Failure | Error code | User message | Placement | Recovery action |
|---|---|---|---|---|---|
| Indizierung starten | Modell fehlt | INDEXING_MODEL_UNAVAILABLE | Das gewählte Embedding-Modell ist nicht verfügbar. | Indizierungsformular | Modell wechseln oder Provider prüfen |
| Indizierung starten | OpenAI nicht bestätigt | INDEXING_CLOUD_CONFIRMATION_REQUIRED | Diese Indizierung würde Originaltexte an OpenAI senden. | Indizierungsformular | bestätigen oder lokalen Provider wählen |
| Indizierung abbrechen | Job nicht mehr abbrechbar | INDEXING_CANCEL_NOT_AVAILABLE | Diese Indizierung kann nicht mehr abgebrochen werden. | Indizierungskarte | Liste aktualisieren |
| Cluster-Set erzeugen | Indizierung nicht fertig | INDEXING_NOT_COMPLETE | Diese Indizierung ist noch nicht abgeschlossen. | Cluster-Set-Formular | fertige Indizierung wählen |
| Explorer exportieren | keine Zeilen | EXPLORER_EXPORT_EMPTY | Es gibt keine exportierbaren Zeilen im aktuellen Filterstand. | Export-Abschnitt | Filter ändern |

### Error presentation levels

- Inline field error: Format-, Pflicht- und Wertebereichsfehler.
- Form-level banner: fehlgeschlagene Start-, Bestätigungs- oder Provideraktionen.
- Component-level error: betroffene Jobkarte, Tabelle, Dialog oder Exportbereich.
- Page-level error: primärer Projekt-/Explorerinhalt kann nicht geladen werden.
- Toast or transient notification: nur sekundäres, nicht-blockierendes Feedback.
- Fatal application fallback: unerwarteter Render-/App-Fehler mit sicherer
  Rückkehr- oder Reload-Aktion.

### Input preservation

Dataset-, Provider-, Modell- und Parameter-Auswahl bleiben bei fehlgeschlagenem
Start erhalten. Such-/Filterzustände und getippte Anzeigenamen bleiben bei
fehlgeschlagenen nachgelagerten Aktionen erhalten, sofern das sicher ist.

### Focus behavior

- Field validation failure: Fokus bleibt im Formular und Fehlermeldung ist
  semantisch zugeordnet.
- Form submission failure: Fokus bleibt im Arbeitsbereich; Fehlerbanner ist
  erreichbar.
- Page-level load failure: Fokus liegt auf Reload- oder Rückkehraktion.
- Dialog action failure: Fokus bleibt im Dialog oder kehrt zur auslösenden Aktion
  zurück, wenn der Dialog geschlossen wird.

### Recovery behavior

- Retry: Provider-/Job-/Listenaktionen können erneut versucht werden, wenn
  retryable.
- Reload: Listen und Explorer-Zustand können neu geladen werden.
- Reauthenticate: nur bei Authentifizierungsfehlern.
- Return to previous page: bei nicht ladbarem Projekt-/Explorerinhalt.
- Contact support: nicht primärer lokaler MVP-Pfad; sichere Korrelation bleibt
  möglich.
- Resolve conflict: bei nicht mehr abbrechbaren oder gelöschten Ressourcen.
- Correct input: bei Modell-, Provider-, Zahlen- oder Bestätigungsfehlern.

### Unknown error fallback

- User-facing title: Aktion fehlgeschlagen.
- User-facing explanation: Die Aktion konnte unerwartet nicht abgeschlossen werden.
  Bitte erneut versuchen.
- Correlation ID placement: im betroffenen Fehlerbereich, wenn vorhanden.
- Support instruction: lokale Diagnose anhand sicherer Job-/Request-ID.
- Input preservation: sichere Formularauswahl und Filter bleiben erhalten.
- Retry behavior: Wiederholen oder Liste/Ansicht neu laden.

### Error-state evidence

- Mockup: `.ai/work/chg-004-analyst-clustering-redesign/prototype`
- Prototype: `.ai/work/chg-004-analyst-clustering-redesign/prototype`
- Storybook: not-applicable; kein Storybook-Prototyp.
- Browser screenshots: nach Produktionsimplementierung unter
  `.ai/work/chg-004-analyst-clustering-redesign/evidence/ui/`.

## Prototype or mockup plan

Der isolierte Click-Dummy zeigt Informationsarchitektur, Tab-Struktur,
Listen-/Panel-Komposition und sekundäres Overlay-Feedback. Produktionscode wird
neu in der bestehenden React-/API-Architektur implementiert.

## Prototype isolation

- Production imports allowed: no
- Production build inclusion allowed: no
- Production backend connection allowed: no
- Production runtime dependency allowed: no
- Mock data or local fixtures: invented static mock data only.
- Private and non-deployable: yes; prototype README declares not production code.
- Required tool dependencies and owning package: none; static HTML/CSS/JS only.

## Mockup or prototype evidence

Der bestätigte Artefaktpfad ist
`.ai/work/chg-004-analyst-clustering-redesign/prototype`. Der Prototyp enthält
`README.md` und `index.html` und bleibt außerhalb von `frontend/src`.

## Prototype promotion decisions

| Prototype element | Decision | Target path | Target layer/responsibility | Tests | Story | Accessibility | Catalog update |
|---|---|---|---|---|---|---|---|
| Navigation labels and project tab order | implement-page-composition | `frontend/src/App.tsx` | project workspace IA | frontend tests | not-applicable | keyboard tabs | no shared entry |
| Indexing panel/list structure | create-feature-local-component | `frontend/src/App.tsx` | Indizierung form/list | API/UI tests | not-applicable | status/alert semantics | feature-local note |
| Cluster explorer table direction | create-feature-local-component | future T4 path | Explorer dense analysis | component/browser tests | not-applicable | real table semantics | feature-local note |
| Prototype CSS/static data | discard-prototype-only-code | not-applicable | temporary mockup only | not-applicable | not-applicable | not-applicable | not-applicable |

## Open design decisions

Keine offenen Designentscheidungen für T2. Exakte Tabellenpaginierung und
Quellen-Dialog-Umsetzung bleiben spätere Implementierungsdetails innerhalb der
akzeptierten Richtung.

## Approval

- Decision: approved
- Approved direction: Analystenworkflow Import → Indizieren → Cluster-Sets →
  Explorer mit profilfreier Indizierung und table-first Explorer-Richtung.
- Approved artifact or revision: `.ai/work/chg-004-analyst-clustering-redesign/prototype`
- Approval type: human
- Approved by: anfordernder Product Owner
- Date: 2026-08-04
