# Feature discovery: Analystenorientierte Indizierungs- und Clusteranalyse

- Requirement ID: CHG-004
- Status: confirmed
- Facilitator/agent: Codex
- Decision owner: anfordernder Product Owner
- Last updated: 2026-08-03

## Discovery trigger

Der Änderungswunsch ersetzt zentrale Domänenbegriffe, Navigation, Persistenz,
Providerkonfiguration, Clustering-Lebenszyklus und den primären Analysebildschirm.
Das ist kein direkt implementierbarer UI-Fix, sondern eine neue fachliche
Arbeitsweise auf bestehenden Projekt-, Import-, Provider-, Embedding- und
Cluster-Grundlagen.

## Current shared-understanding summary

Das Tool soll lokal und privat bleiben. Der Nutzer will Support-Datensätze bequem
indizieren, mehrfach clustern, Cluster fachlich verstehen und iterativ
verfeinern. Analyseprofile werden ersatzlos entfernt. „Runs“ wird zu
„Indizieren“. Clustering erzeugt persistente Cluster-Sets auf Basis einer
Indizierung. Der Explorer wird eine tabellarische Analyseansicht mit
LLM-generierten Clusterzusammenfassungen und einem Quellen-Dialog.

## Decision tree

| ID | Decision or question | Depends on | Recommended answer | User decision | Status |
|---|---|---|---|---|---|
| D001 | Fachlicher Ersatz für Analyseprofile | none | Analyseprofile vollständig entfernen; Embedding-Konfiguration gehört zur Indizierung, Cluster-/LLM-Konfiguration zum Cluster-Set. | bestätigt | confirmed |
| D002 | Begriff für bisherige Runs | D001 | `Indizierung` / `IndexingRun`; UI-Tab „Indizieren“. | bestätigt | confirmed |
| D003 | Embedding-Quelle | D002 | Indizierung erzeugt immer Embeddings für Kundenanfrage (`message`) und Supportantwort (`answer`); Cluster-Sets wählen später die Vektorbasis. | bestätigt: immer beide einbetten | confirmed |
| D004 | Cluster-Ergebnis-Lebenszyklus | D002 | Neues persistentes `ClusterSet` pro Berechnung; Cluster referenzieren Cluster-Set statt direkt Run. | bestätigt | confirmed |
| D005 | LLM-Zusammenfassungspflicht | D004 | LLM-Zusammenfassung verwenden, wenn LLM eingerichtet/gewählt ist; ohne eingerichtetes LLM bleibt Clustering möglich und Zusammenfassungsfelder bleiben sichtbar nicht generiert. | bestätigt | confirmed |
| D006 | LLM Provider | D005 | Globaler Tab „LLM-Provider“ getrennt von „Embedding-Provider“, zunächst OpenAI und Ollama. | bestätigt | confirmed |
| D007 | Clusterkategorien | D005 | Start mit freier LLM-Kategorie plus manueller Korrektur; spätere Taxonomie möglich. | bestätigt | confirmed |
| D008 | Hierarchische Exploration | D004 | Jedes Cluster-Set kann Eltern-Set und Quellfilter speichern; neue feinere Sets werden aus eingeschlossenen Clustern/Members erzeugt. | bestätigt | confirmed |
| D009 | Ausschluss-Workflow | D008 | Clusterstatus `active/excluded/reviewed` oder äquivalent; ausgeschlossene Cluster separat anzeigen und wieder einschließen. | bestätigt | confirmed |
| D010 | Kandidaten-Workflow | none | Kandidaten als eigenständiges finales Artefakt entfernen; Cluster-Set ist das finale Analyseergebnis. | bestätigt | confirmed |
| D011 | Datenmigration | D001, D004, D010 | Importierte Projekte/Datasets behalten; alte Profile, Runs, Embeddings, Cluster und Candidates dürfen in lokaler Migration entfernt werden. | bestätigt | confirmed |
| D012 | LLM-Beispielauswahl | D005 | Nutzer gibt eine Zahl ab 1 ein oder wählt „Alle Beispiele“; Werte über Clustergröße werden je Cluster auf alle verfügbaren Beispiele begrenzt; Beispiele werden zufällig gezogen; Sample-Strategie und Seed werden gespeichert. | bestätigt | confirmed |
| D013 | Projektübersicht | none | Hauptpunkt „Projekte“ zeigt Projektübersicht; einzelne Projekte erscheinen als Unterpunkte links. | bestätigt | confirmed |
| D014 | Importlöschung | D013 | Imports/Datasets können gelöscht werden; abhängige Indizierungen und Cluster-Sets bleiben bestehen und zeigen gelöschte Quelle. | bestätigt | confirmed |
| D015 | Indizierungslöschung | D004 | Indizierungen können gelöscht werden; abhängige Cluster-Sets bleiben bestehen und zeigen gelöschte Indizierung. | bestätigt | confirmed |
| D016 | Cluster-Set-Verwaltung | D004 | Cluster-Sets können umbenannt und gelöscht werden; ableitende Bearbeitung heißt in der UI „Cluster verfeinern“, weil ein neues Child-Set entsteht. | bestätigt | confirmed |
| D017 | Explorer-Suche | D004 | Erstes Suchfeld ist Textsuche über sichtbare Clusterfelder; semantische Suche wird später als eigener Modus geplant. | bestätigt | confirmed |
| D018 | Verfeinerungsaktion | D008 | „Eingeschlossene Cluster verfeinern“ öffnet Cluster-Set-Erzeugung mit Eltern-Set/Quellen vorbefüllt und erstellt ein neues Child-Set. | bestätigt | confirmed |
| D019 | Outlier- und Mismatch-Analyse | D004 | Outlier-Management mit Thresholds und Frage/Antwort-Mismatch-Hinweisen wird in Explorer und Cluster-Set-Parametern berücksichtigt. | bestätigt | confirmed |
| D020 | Kombinierte und zweistufige Vektorbasis | D003, D008 | Kombinierte Basis clustert Support-Paare über gewichtete Konkatenation normalisierter Anfrage-/Antwort-Embeddings; Child-Cluster-Sets können eine andere Vektorbasis als das Eltern-Set wählen. | bestätigt | confirmed |
| D021 | Analyse-Lineage und Bearbeitungshistorie | D004, D008 | Strukturändernde Bearbeitungen erzeugen Child-Cluster-Sets mit Parent-Verweis und Quellen-Snapshot; nicht-strukturelle Bearbeitungen werden als Ereignisse protokolliert; UI zeigt einen aufklappbaren Analysebaum und Explorer-Analysepfad. | bestätigt | confirmed |
| D022 | Explorer-Export und LLM-Sample-Default | D005, D017 | Defaultwert für zufällige LLM-Beispiele ist 10; es gibt keinen Export-Tab; der Explorer besitzt einen eigenen Export-Abschnitt für den aktuellen Such-/Filterstand als CSV oder JSON. | bestätigt | confirmed |

## Recommended interview order

Alle produktentscheidenden Fragen aus dem ersten Interview und der Mockup-Review
sind beantwortet. Der aktualisierte Mockup-/Entwurfsstand ist freigegeben.

## Confirmed decisions

- Das Tool ist für privaten lokalen Gebrauch gedacht, nicht als öffentliches
  Online-Tool.
- Funktionalität und bequeme Analyse stehen vor SaaS-Politur.
- Analyseprofile sollen vollständig entfernt werden.
- Rückwärtskompatibilität für Analyseprofile ist nicht erforderlich.
- „Runs“ entspricht faktisch Indizierung und soll umbenannt werden, falls diese
  Interpretation zutrifft.
- Eine Indizierung erzeugt immer Embeddings für Kundenanfrage und Supportantwort.
- Cluster-Sets wählen die Vektorbasis aus den vorhandenen Embeddings.
- Clustering soll auf einer gewählten Indizierung basieren.
- Mehrere Clusterberechnungen pro Indizierung sollen möglich sein.
- Cluster-Sets sollen gespeichert und später geladen werden können.
- Geladene Cluster-Sets sollen mit neuen Parametern als neues Child-Set verfeinert
  werden.
- LLM-Zusammenfassung soll verwendet werden, wenn ein LLM eingerichtet ist.
- Ohne eingerichtetes LLM soll Clustering trotzdem möglich bleiben.
- Der Nutzer kann eine Beispielanzahl ab 1 oder „Alle Beispiele“ als Basis der
  LLM-Zusammenfassung wählen; Werte über Clustergröße werden je Cluster begrenzt.
- Die Beispiele werden zufällig gezogen.
- Der Explorer soll tabellarisch statt kartenzentriert werden.
- Cluster-Titel, Kategorie, zusammengefasste Frage und zusammengefasste Antwort
  sollen per LLM generiert werden.
- LLM-Provider sollen wie Embedding-Provider in den Einstellungen konfigurierbar
  sein.
- Clusterkategorien starten als freie LLM-Kategorien mit manueller Korrektur.
- Vorhandene lokale abgeleitete Daten wie alte Analyseprofile, Runs, Embeddings,
  Cluster und Candidates dürfen gelöscht werden.
- Kandidaten sind im neuen Workflow überflüssig; das Cluster-Set ist das finale
  Analyseergebnis.
- Projekte können in einer Projektübersicht angelegt, umbenannt, geöffnet und
  gelöscht werden; einzelne Projekte erscheinen links unter „Projekte“.
- Imports erhalten editierbare Anzeigenamen und können gelöscht werden, ohne
  abhängige Indizierungen oder Cluster-Sets zu löschen.
- Indizierungen können gelöscht werden, ohne abhängige Cluster-Sets zu löschen.
- Cluster-Sets können umbenannt und gelöscht werden.
- Explorer-Suche ist zunächst Textsuche; semantische Suche wird nicht implizit
  vermischt.
- Verfeinerung erzeugt ein neues Child-Cluster-Set aus eingeschlossenen Quellen;
  die zweite Stufe kann eine andere Vektorbasis nutzen, z. B. zuerst
  Kundenanfragen, danach Supportantworten.
- Analysebaum und Analysepfad machen Parent-Sets, Quellen-Snapshots und
  Bearbeitungsschritte nachvollziehbar.
- Outlier-Management und Frage/Antwort-Mismatch-Hinweise sind Teil des
  Analyseworkflows.
- Defaultwert für zufällige LLM-Beispiele je Cluster ist 10.
- Es gibt keinen separaten Export-Tab; der Explorer besitzt einen eigenen
  Export-Abschnitt und exportiert den aktuellen Such-/Filterstand wahlweise als
  CSV oder JSON.

## Rejected alternatives

- Analyseprofile als zentrale Konfiguration behalten: verworfen, weil sie die
  gewünschten Entscheidungszeitpunkte vermischen.
- Cluster weiterhin eindeutig an eine einzelne Indizierung ohne Set-Konzept binden:
  verworfen, weil mehrfache Berechnungen und abgeleitete Verfeinerungen sonst nicht sauber
  geladen oder verglichen werden können.
- Explorer als Kartenliste beibehalten: verworfen, weil tabellarische Analyse,
  Gruppierung und Quellenprüfung im Vordergrund stehen.

## Open questions and blockers

Keine offenen Produktentscheidungen für den Entwurf.

## Proposed scope

### In scope

- Neuer Workflow Import → Indizieren → Cluster-Sets → Explorer.
- Entfernen von Analyseprofilen.
- Neue LLM-Provider-Einstellungen.
- Persistente Cluster-Sets inklusive LLM-Zusammenfassung.
- Hierarchische Cluster-Set-Verfeinerung.
- Ausschließen/Wiedereinschließen von Clustern.
- Quellen-Dialog für echte Kundenanfragen und Supportantworten.
- Kandidatenkonzept aus dem neuen Analyseworkflow entfernen.

### Out of scope / non-goals

- Produktionszugriff.
- Öffentliche SaaS-Funktionalität.
- Live-Integrationen.
- Automatische rechtliche/fachliche Freigabe generierter Inhalte.

## Draft success and acceptance criteria

- [x] Der Nutzer kann ohne Verständnis technischer „Profile“ nachvollziehbar
  indizieren, clustern und explorieren.
- [x] Jeder wichtige Analyseentscheid ist dort konfigurierbar, wo er getroffen wird:
  Embedding bei Indizierung, Vektorbasis/Algorithmus/LLM bei
  Cluster-Set-Erzeugung.
- [x] Der Explorer beantwortet auf einen Blick: Was ist das Thema, welche Kategorie,
  welche Kundenfrage, welche Antwort, wie viele Quellen?
- [x] Echte Quellen sind schnell prüfbar, aber nicht permanent unübersichtlich in der
  Hauptansicht eingebettet.
- [x] Das Cluster-Set ersetzt Kandidaten als finales Analyseergebnis.

## Shared-understanding confirmation

- User explicitly confirmed shared understanding: yes
- Confirmed by: anfordernder Product Owner
- Confirmation date: 2026-08-04
- Corrections or conditions: keine verbleibenden Produktfragen
