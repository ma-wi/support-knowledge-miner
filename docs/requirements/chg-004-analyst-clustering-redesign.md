# Requirement: Analystenorientierte Indizierungs- und Clusteranalyse

- Requirement ID: CHG-004
- Work type: incremental-change
- Status: accepted
- Affected capability specifications:
  `docs/specifications/support-knowledge-miner-mvp1.md`,
  `docs/specifications/local-runtime-providers.md`
- Work directory: `.ai/work/chg-004-analyst-clustering-redesign/`
- Decision owner: anfordernder Product Owner
- Last updated: 2026-08-04

## Problem

Die aktuelle Oberfläche und Domänensprache bilden nicht den eigentlichen
Analyseprozess ab. Analyseprofile bündeln Embedding-Modell, Cluster-Parameter und
Prompt-/LLM-Aspekte in einem Projektartefakt, obwohl diese Entscheidungen getrennt
getroffen und mehrfach ausprobiert werden müssen. Der Tab „Runs“ zeigt faktisch
Embedding-Erzeugung, ist aber nicht als Indizierung benannt. Clustering ist an einen
Run gebunden und kann nicht sauber als mehrfach berechenbares, ladbares Ergebnis-Set
verwaltet werden.

Der aktuelle Cluster Explorer ist für analytische Arbeit unzureichend: Er zeigt
Cluster als Karten, bietet keine tabellarische Übersicht mit fachlich
zusammengefassten Fragen/Antworten und öffnet Quellen nicht in einem fokussierten
Dialog. Der Tab „Kandidaten“ ist in der aktuellen Form unverständlich und soll aus
dem primären Workflow entfernt werden.

## Desired outcome

Das Tool führt Analysten durch einen klaren lokalen Workflow:

1. Datensatz importieren.
2. Datensatz mit einem gewählten Embedding-Modell indizieren.
3. Auf Basis einer gewählten Indizierung ein oder mehrere Cluster-Sets mit
   konfigurierbarer Vektorbasis, Algorithmus und optionaler LLM-Zusammenfassung
   erzeugen.
4. Persistierte Cluster-Sets laden, vergleichen, mit geänderten Parametern als
   neues Child-Set verfeinern.
5. Cluster in einer dichten Tabelle explorieren, gruppieren, ausschließen und bei
   Bedarf hierarchisch weiter verfeinern.
6. Echte Kundenanfragen und Supportantworten eines Clusters in einem Dialog prüfen.

Analyseprofile entfallen vollständig. Es muss keine Rückwärtskompatibilität für
Analyseprofile erhalten bleiben.

## Users and stakeholders

- Primärer Nutzer: Analyst/Kurator, der private Support-Datensätze lokal clustert
  und Themenbereiche analysiert.
- Betreiber: lokaler Nutzer der Docker-Compose-Umgebung.
- Datenschutzrelevant: importierte Kundenanfragen und Supportantworten können
  personenbezogene oder sensible Inhalte enthalten.

## Functional requirements

- FR-1: Die Anwendung darf keine Analyseprofile mehr im UI-Workflow, im öffentlichen
  neuen API-Vertrag, in neuen Domänenmodellen oder in neuen Lauf-Snapshots verwenden.
- FR-2: Der bisherige „Runs“-Workflow wird fachlich in „Indizieren“ umbenannt.
- FR-3: Eine Indizierung wählt Dataset-Version, Embedding-Provider,
  Embedding-Modell und Embedding-Parameter explizit aus.
- FR-4: Eine Projektansicht kann mehrere Indizierungen über denselben oder
  unterschiedliche Dataset-Versionen speichern und laden.
- FR-5: Eine Indizierung erzeugt für jedes gültige Support-Paar je ein Embedding
  für die Kundenanfrage (`message`) und die Supportantwort (`answer`).
- FR-6: Embeddings bleiben als persistierte Vektoren mit Textvariante, Modell-,
  Parameter-, Dataset-, Projekt- und Laufprovenienz nachvollziehbar.
- FR-7: Clustering wird auf Basis einer ausgewählten abgeschlossenen Indizierung
  gestartet.
- FR-8: Beim Clustering wählt der Nutzer die Vektorbasis für die Clusterbildung:
  Kundenanfragen, Supportantworten oder eine kombinierte Basis aus beiden
  vorhandenen Embeddings. Geclustert wird immer pro Support-Paar. Bei der
  kombinierten Basis wird aus dem normalisierten Kundenanfrage-Embedding und dem
  normalisierten Supportantwort-Embedding desselben Paares ein gewichteter
  gemeinsamer Paar-Vektor gebildet; Standard ist 50 % Anfrage und 50 % Antwort.
- FR-9: Beim Clustering sind Algorithmus und Cluster-Parameter pro Cluster-Set
  konfigurierbar.
- FR-10: Beim Clustering kann ein LLM-Provider/-Modell für die Generierung von
  Clustertitel, Clusterkategorie, zusammengefasster Frage und zusammengefasster
  Antwort konfiguriert werden; wenn kein LLM eingerichtet ist, bleibt Clustering
  ausführbar und die Zusammenfassungsfelder werden als nicht generiert angezeigt.
- FR-11: Für LLM-Zusammenfassungen kann der Nutzer per Zahlenfeld festlegen, wie
  viele zufällig gezogene Beispielpaare als Basis verwendet werden. Der Wert muss
  mindestens 1 sein und ist nach oben nicht künstlich begrenzt. Standardwert ist
  10; übersteigt der Wert die Clustergröße, werden alle verfügbaren Beispiele
  dieses Clusters verwendet.
- FR-12: Die zufällige Beispielziehung wird mit Seed/Strategie als Provenienz
  gespeichert, damit ein Cluster-Set nachvollziehbar bleibt.
- FR-13: LLM-Provider werden global in den Einstellungen unter einem eigenen Tab
  „LLM-Provider“ konfiguriert.
- FR-14: LLM-Provider unterstützen mindestens lokale Ollama-Modelle und OpenAI
  Cloud-Modelle mit expliziter Cloud-Warnung vor dem Senden von Originaltexten.
- FR-15: Ein Cluster-Set speichert Vektorbasis, Algorithmus, Parameter, gewählte
  Indizierung, LLM-Konfiguration, Sample-Strategie, Status, Zeitstempel, Fehler und
  Ergebnisprovenienz.
- FR-16: Eine Indizierung kann mehrere Cluster-Sets besitzen.
- FR-17: Ein geladenes Cluster-Set kann über die Aktion „Cluster verfeinern“ als
  neues Child-Cluster-Set mit geänderten Parametern, Vektorbasis oder Quellmenge
  abgeleitet werden, ohne das geladene Set zu überschreiben.
- FR-18: Die Cluster-Explorer-Ansicht zeigt eine tabellarische Übersicht mit
  Clustertitel, Clusterkategorie, zusammengefasster Frage, zusammengefasster
  Antwort, Anzahl Kundenanfragen, Anzahl Supportantworten und Aktionen.
- FR-19: Die Tabellenansicht kann nach Clusterkategorie gruppieren.
- FR-20: Cluster können von der weiteren Betrachtung ausgeschlossen und separat
  sichtbar gemacht werden.
- FR-21: Ausgeschlossene Cluster können wieder eingeschlossen werden.
- FR-22: Der Nutzer kann echte Kundenanfragen und Supportantworten eines Clusters in
  einem Dialogfenster ansehen.
- FR-23: Der Dialog zeigt `ticket_id`, `message_group_id`, Kundenanfrage,
  Supportantwort, Zugehörigkeits-Score und Zuordnungsart.
- FR-24: Der Nutzer kann ausgewählte oder nicht ausgeschlossene Cluster als Basis
  für eine weitere, feinere Clusterung verwenden. Diese zweite Stufe kann eine
  andere Vektorbasis als das Eltern-Set wählen, zum Beispiel zuerst grob nach
  Kundenanfragen und danach innerhalb der verbleibenden Quellen nach
  Supportantworten.
- FR-25: Die feinere Clusterung speichert einen Verweis auf das Eltern-Cluster-Set
  und die eingeschlossene Quellmenge.
- FR-26: Der Tab „Kandidaten“ wird aus der Projekt-Navigation entfernt.
- FR-27: Kandidaten werden als eigenständiges finales Artefakt entfernt; das
  finale Analyseergebnis ist das Cluster-Set mit Clusterzusammenfassungen,
  manuellen Korrekturen, Ausschlusszustand und Quellen-Traceability.
- FR-28: Bestehende Candidate-Exportbedarfe werden nicht über den alten
  Kandidatenworkflow fortgeführt. Export ist Teil des Explorers, nicht ein eigener
  Projekt-Tab.
- FR-29: Die Hauptnavigation „Projekte“ öffnet eine Projektübersicht mit
  Projekt-anlegen, Projekt-umbenennen, Projekt-öffnen und Projekt-löschen.
  Projekte haben zunächst keinen fachlichen Lebenszyklusstatus; „aktiv“ bedeutet
  nur „aktuell geöffnet“ und wird als UI-Auswahl dargestellt, nicht als dauerhaft
  gespeicherter Projektstatus.
- FR-30: Einzelne Projekte erscheinen als Unterpunkte der linken Projektnavigation
  und öffnen den jeweiligen Projekt-Workspace.
- FR-31: Die Importübersicht zeigt mehrere Imports/Dataset-Versionen und erlaubt
  einen editierbaren Anzeigenamen je Import. Namensänderungen werden ohne
  separaten „Namen speichern“-Button automatisch gespeichert.
- FR-32: Imports/Dataset-Versionen können gelöscht werden. Indizierungen und
  Cluster-Sets, die diese Daten nutzen, bleiben bestehen; betroffene Indizierungen
  zeigen „Datensatz gelöscht“.
- FR-33: Indizierungen können gelöscht werden. Cluster-Sets, die diese Indizierung
  nutzen, bleiben bestehen; betroffene Cluster-Sets zeigen „Indizierung gelöscht“
  und können exportiert oder aus einer anderen Indizierung neu geclustert werden.
- FR-34: Cluster-Sets können umbenannt und gelöscht werden. Namensänderungen
  werden ohne separaten „Namen speichern“-Button automatisch gespeichert. Wenn
  ein gelöschtes Cluster-Set Parent von anderen Sets ist, bleibt ein
  nicht-ladbarer Historienknoten mit ID, Name, Ursprungstyp und Parametern im
  Analysebaum erhalten.
- FR-35: Die LLM-Beispielanzahl ist ein Zahlenfeld mit Mindestwert 1 und optionaler
  Checkbox „Alle Beispiele verwenden“. Wenn der eingegebene Wert größer als die
  Clustergröße ist, nutzt das System alle verfügbaren Beispiele dieses Clusters.
  Die echte UI und API akzeptieren nur positive ganze Zahlen; Buchstaben,
  Dezimalwerte, Exponentnotation, 0 und negative Werte sind ungültig.
- FR-36: Der Explorer besitzt eine klar beschriftete Textsuche über Titel,
  Kategorie, zusammengefasste Frage und zusammengefasste Antwort; semantische Suche
  wird nicht implizit mit diesem Suchfeld vermischt. Suche und Filter ändern nur
  die Ansicht, nicht das gespeicherte Cluster-Ergebnis.
- FR-37: „Eingeschlossene Cluster verfeinern“ öffnet die Cluster-Set-Erzeugung mit
  Eltern-Cluster-Set und eingeschlossenen Quellen vorbefüllt; der Start erzeugt ein
  neues Child-Cluster-Set und verändert das Eltern-Set nicht.
- FR-38: Cluster-Sets unterstützen Outlier-Management mit algorithmusspezifischen
  Outlier-Signalen und einem globalen sowie optional clusterlokalen Threshold.
  Das Entfernen von Ausreißern ist fachlich von Suche/Filter getrennt, wird aber
  als eigene Box innerhalb des Cluster Explorers direkt unter Suche/Filter
  dargestellt. Es wird über eine eigene Aktion „Ausreißer berechnen“ im Bereich
  „Ausreißer ausschließen“ ausgeführt; das Ergebnis wird als neues Cluster-Set
  gespeichert. Der Box-Header zeigt keinen zusätzlichen Status-Tag wie „ändert
  Ergebnis“.
- FR-39: Die Explorer-Tabelle kann Frage/Antwort-Mismatch-Hinweise anzeigen,
  insbesondere wenn nach Supportantworten geclustert und innerhalb eines Clusters
  Fragen oder Antworten fachlich nicht zusammenpassen.
- FR-40: Click-Dummy-/UI-Feedback erscheint als nicht-blockierendes Overlay/Popup,
  ist wegklickbar, verschwindet automatisch und verschiebt keine darunterliegenden
  Inhalte.
- FR-41: Jedes Cluster-Set speichert seine Ableitung als nachvollziehbare
  Provenienz: Ursprungstyp, Parent-Cluster-Set falls vorhanden, verwendete
  Parent-Cluster oder Quellen-Snapshot, Vektorbasis, Algorithmus, Parameter,
  Ausreißer-/Filterparameter, LLM-Konfiguration, Erstellzeit und auslösende Aktion.
- FR-42: Die Cluster-Set-Übersicht zeigt gespeicherte Sets als aufklappbaren
  Analysebaum. Root-Sets hängen an der Indizierung; Child-Sets hängen unter ihrem
  Parent-Set. Der Nutzer kann Parent/Child laden, Historie anzeigen und Äste
  ein- oder ausklappen.
- FR-43: Der Explorer zeigt für das geladene Cluster-Set einen Analysepfad mit
  Import, Indizierung, Parent-Cluster-Sets und den relevanten Bearbeitungsschritten.
- FR-44: Strukturändernde Bearbeitungen wie Verfeinerung, Ausreißer-Ausschluss,
  Wechsel der Vektorbasis, Änderung von Clusteralgorithmus/-parametern oder
  Quellenänderungen erzeugen ein neues Child-Cluster-Set. Nicht-strukturändernde
  Bearbeitungen wie Umbenennung oder manuelle Textkorrektur werden als
  Bearbeitungsereignis am bestehenden Set protokolliert.
- FR-45: Indizierungen und Cluster-Set-Erzeugungen/-Verfeinerungen laufen als
  Jobs mit sichtbarem Status, Prozentfortschritt, aktueller Phase, Startzeit und
  sicherer Fehlermeldung. Laufende Jobs zeigen die Prozentangabe direkt im
  Status-Chip, können abgebrochen werden und sind erst ladbar bzw. als Basis
  nutzbar, wenn der Status „fertig“ erreicht ist. Neue oder laufende
  Indizierungen erscheinen in der Indizierungsübersicht als fokussierte Karte.
  Neue oder laufende Cluster-Set-Jobs erscheinen in der Cluster-Set-Übersicht als
  expandierter und fokussierter Baumknoten. Die linken Formulare zeigen keine
  separaten Fortschrittscontainer.
- FR-46: Der Projektkopf zeigt keinen rechten allgemeinen Verbindungs-/Status-Tag
  wie „lokal verbunden“.
- FR-47: Der Explorer bietet einen eigenen Export-Abschnitt als eigenen Container
  auf Explorer-Ebene. Er steht nicht im Header oder Container der tabellarischen
  Analyse und ist getrennt von Suche/Filter und Ausreißer-Management. Exportiert
  wird der aktuelle Such-/Filterstand der Explorer-Tabelle wahlweise als CSV oder
  JSON. Der Export ist ans geladene Cluster-Set, dessen Filterzustand und dessen
  sichtbare Tabellenfelder gebunden. Der Export-Header zeigt keinen zusätzlichen
  Status-Tag.

## Non-functional requirements

- Security/privacy: Original Supporttexte dürfen nur an OpenAI gesendet werden,
  wenn der Nutzer die Cloud-Nutzung für die konkrete Indizierung oder
  Cluster-Zusammenfassung bestätigt. Lokale Ollama-Endpunkte bleiben auf erlaubte
  lokale Hosts beschränkt. Secrets bleiben write-only.
- Local-first: Die Anwendung bleibt ein lokales privates Tool ohne Produktionszugriff
  und ohne öffentliches Online-SaaS-Ziel.
- Performance: Clustering darf weiterhin keine vollständige paarweise Distanzmatrix
  über alle Datensätze erzeugen. LLM-Zusammenfassungen müssen über Sampling,
  Token-/Textgrenzen, Timeouts und Batches begrenzt sein.
- Reliability: Ein fehlgeschlagenes Cluster-Set darf keine partiellen
  Analyseergebnisse als erfolgreich anzeigen. Bereits gespeicherte Cluster-Sets
  bleiben unverändert.
- Usability: Funktionalität und bequeme Exploration haben Priorität vor
  marktreifer SaaS-Politur.
- Accessibility: Tabellen, Dialoge, Statusmeldungen und Fehlermeldungen müssen
  tastaturbedienbar und semantisch unterscheidbar sein.

## In scope

- Entfernung des Analyseprofil-Konzepts aus dem aktiven Workflow.
- Umbenennung und Neuformung von „Runs“ zu „Indizieren“.
- Neues Cluster-Set-Modell für wiederholbare Clusterberechnungen.
- LLM-Provider-Konfiguration getrennt von Embedding-Provider-Konfiguration.
- Optionale LLM-generierte Cluster-Zusammenfassungen mit konfigurierbarer
  zufälliger Beispielanzahl je Cluster.
- Neuer tabellarischer Cluster Explorer mit Quellen-Dialog.
- Gruppieren, Ausschließen und hierarchisches Verfeinern von Cluster-Sets.
- Projektübersicht und linke Projekt-Unterpunkte.
- Import-/Indizierungs-/Cluster-Set-Umbenennen und Löschsemantik.
- Textsuche, Outlier-Management und Frage/Antwort-Mismatch-Hinweise.
- Entfernung des Kandidaten-Tabs und des eigenständigen Kandidatenkonzepts aus dem
  neuen Analyseworkflow.
- Migration lokaler Entwicklungsdaten ohne Profil-Rückwärtskompatibilität.
- Aktualisierung von Requirements, Spezifikation, ADRs, Tests und UI-Designartefakten
  nach Bestätigung.

## Out of scope / non-goals

- Produktionszugriff, Produktionsdaten oder Produktionsdeployment.
- Live-Integrationen in Ticket-, Shop-, ERP- oder Kommunikationssysteme.
- Öffentliche Mehrmandanten-SaaS-Anforderungen.
- Vollautomatische fachliche Freigabe generierter Wissensartikel.
- Perfekte Clusterqualität ohne Analystenprüfung.
- Rückwärtskompatibilität für Analyseprofile.

## Acceptance criteria

- [x] AC-1: Projekt-Navigation und neue Verträge enthalten keine
  Analyseprofile mehr; relevante alte Artefakte sind entfernt oder explizit
  migriert.
- [x] AC-2: Ein Nutzer kann eine Dataset-Version auswählen, ein Embedding-Modell
  wählen und eine Indizierung starten, die je Support-Paar Embeddings für
  Kundenanfrage und Supportantwort erzeugt.
- [x] AC-3: Mehrere Indizierungen desselben Datensatzes mit unterschiedlichen
  Embedding-Modellen werden gespeichert, geladen und unterscheidbar angezeigt.
- [x] AC-4: Ein Nutzer kann eine abgeschlossene Indizierung auswählen,
  Cluster-Vektorbasis, Cluster-Algorithmus/-Parameter, optionales LLM-Modell und
  LLM-Beispielanzahl konfigurieren und ein Cluster-Set erzeugen.
- [x] AC-5: Mehrere Cluster-Sets pro Indizierung können gespeichert, geladen und
  anhand von Algorithmus, Parametern, LLM-Modell, Erstellzeit und Status
  unterschieden werden.
- [x] AC-6: Ein geladenes Cluster-Set kann über „Cluster verfeinern“ mit
  geänderten Parametern als neues Child-Cluster-Set erzeugt werden; das neue
  Ergebnis erhält eine neue Cluster-Set-ID und überschreibt das alte Set nicht.
- [x] AC-7: Der Explorer zeigt Cluster tabellarisch mit Titel, Kategorie,
  zusammengefasster Frage, zusammengefasster Antwort, Kundenanfragen,
  Supportantworten und Aktionen.
- [x] AC-8: Wenn ein LLM eingerichtet und gewählt ist, werden Titel, Kategorie,
  zusammengefasste Frage und Antwort aus zufällig gezogenen Beispielpaaren
  generiert, persistiert und mit Modell-, Prompt-, Sample- und Seed-Provenienz
  gespeichert; ohne LLM bleibt das Cluster-Set mit sichtbar nicht generierten
  Zusammenfassungen nutzbar.
- [x] AC-9: Der Quellen-Dialog eines Clusters zeigt die zugeordneten echten
  Kundenanfragen und Supportantworten mit Traceability-Feldern.
- [x] AC-10: Cluster können nach Kategorie gruppiert, von weiterer Betrachtung
  ausgeschlossen, separat angezeigt und wieder eingeschlossen werden.
- [x] AC-11: Der Nutzer kann aus einer eingeschränkten Quellmenge eine feinere
  Clusterung starten; das neue Cluster-Set verweist auf sein Eltern-Set.
- [x] AC-12: Einstellungen enthalten getrennte Tabs für Embedding-Provider und
  LLM-Provider; OpenAI-Keys werden nicht im Klartext angezeigt.
- [x] AC-13: OpenAI-Nutzung für Embeddings oder LLM-Zusammenfassungen verlangt eine
  explizite Bestätigung direkt vor dem Senden von Originaltexten.
- [x] AC-14: Der Tab „Kandidaten“, die Candidate-Erstellung aus Clustern und das
  eigenständige Kandidatenkonzept sind aus dem neuen Analyseworkflow entfernt; das
  Cluster-Set ist das finale Analyseartefakt.
- [x] AC-15: Fehler bei Indizierung, Clustering, LLM-Zusammenfassung,
  Cluster-Set-Laden und Quellen-Dialog zeigen sichere, konkrete, wiederholbare
  Nutzerhinweise ohne Secrets, Roh-Providerantworten oder unnötige Rohtexte.
- [x] AC-16: Der klickbare Mockup-/Design-Entwurf ist durch den Decision Owner
  bestätigt, bevor Produktionsimplementierung beginnt.
- [x] AC-17: Fokussierte Tests, UI-Tests, Migrations-/Schema-Tests,
  Security-/Dependency-Gates und `./.ai/tools/verify.sh` laufen nach Umsetzung
  erfolgreich; unabhängiger Review hat keine offenen P0/P1-Findings.
- [x] AC-18: Die Projektübersicht erlaubt Projektanlage, Umbenennen, Öffnen und
  Löschen; geöffnete Projekte erscheinen links als Projekt-Unterpunkte; es gibt
  keinen separaten Projektstatus „Entwurf“.
- [x] AC-19: Imports haben editierbare Anzeigenamen und können gelöscht werden,
  ohne bestehende Indizierungen oder Cluster-Sets zu löschen; abhängige
  Indizierungen zeigen den gelöschten Datensatz; Namensänderungen benötigen
  keinen separaten Speichern-Button.
- [x] AC-20: Indizierungen können gelöscht werden, ohne bestehende Cluster-Sets zu
  löschen; abhängige Cluster-Sets zeigen die gelöschte Indizierung und bleiben
  exportierbar.
- [x] AC-21: Cluster-Sets haben editierbare Namen, können gelöscht werden und zeigen
  für alle fertigen gespeicherten Sets die Aktionen „Im Explorer laden“ und
  „Cluster verfeinern“, solange der Zustand dies erlaubt; Namensänderungen benötigen keinen separaten
  Speichern-Button.
- [x] AC-22: LLM-Beispiele werden über Zahlenfeld plus „Alle Beispiele“ konfiguriert;
  Standard ist 10, nur positive ganze Zahlen sind gültig, und Werte oberhalb der
  Clustergröße werden pro Cluster auf die verfügbaren Beispiele begrenzt.
- [x] AC-23: Explorer-Suche ist als Textsuche definiert; Verfeinerung erstellt ein
  neues Child-Cluster-Set aus eingeschlossenen Quellen und kann dabei eine andere
  Vektorbasis als das Eltern-Set nutzen; Suche und Filter verändern keine
  gespeicherten Cluster-Ergebnisse.
- [x] AC-24: Outlier-Management und Frage/Antwort-Mismatch-Hinweise sind im Explorer
  als von Suche/Filter getrennte Berechnung sichtbar und als spätere
  Backend-Parameter/Testseams spezifiziert.
- [x] AC-25: Click-Dummy-Feedback verschiebt keine Layoutinhalte, ist schließbar und
  verschwindet automatisch.
- [x] AC-26: Cluster-Sets sind in der Übersicht als aufklappbarer Parent-/Child-
  Analysebaum sichtbar; der Explorer zeigt den Analysepfad des geladenen Sets.
- [x] AC-27: Jede strukturelle Cluster-Bearbeitung erzeugt ein neues Child-
  Cluster-Set mit unveränderlichem Parent-Verweis und Quellen-Snapshot; reine
  Metadatenbearbeitungen sind als Historienereignisse nachvollziehbar.
- [x] AC-28: Das Löschen eines Parent-Cluster-Sets zerstört die Nachvollziehbarkeit
  vorhandener Child-Sets nicht; die UI zeigt einen gelöschten Historienknoten.
- [x] AC-29: Laufende Indizierungs- und Cluster-Set-Jobs zeigen Status-Chip mit
  Prozentangabe, Progressbar, Phase und Abbrechen-Aktion; Lade-/Weiterverwendungs-
  Aktionen sind bis zum Status „fertig“ deaktiviert; neue Indizierungsjobs werden
  in der Indizierungsübersicht fokussiert, neue Cluster-Set-Jobs im Analysebaum
  expandiert, fokussiert und angesprungen.
- [x] AC-30: Es gibt keinen Projekt-Tab „Export“; der Explorer enthält einen
  eigenen Export-Abschnitt und exportiert den aktuellen Such-/Filterstand als CSV
  oder JSON.

## Open questions

Keine verbleibenden Produktfragen für den Entwurf. Paginierung bleibt
Umsetzungsdetail.

## Approval

- Shared understanding confirmed: yes
- Confirmed by: anfordernder Product Owner
- Confirmation date: 2026-08-04
- Ready for implementation: yes
- Implementation status: verified by CHG-004 T2-T6 focused tests, full gate
  verification and independent review.
- Remaining blockers: none.
