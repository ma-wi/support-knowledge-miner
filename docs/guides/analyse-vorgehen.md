# Kompakter Analyse-Guide

Dieser Guide beschreibt ein pragmatisches Standardvorgehen für eine Support-Knowledge-Analyse im MVP. Die Werte sind Faustregeln für erste Läufe; gute Ergebnisse entstehen durch 2-3 kurze Iterationen, nicht durch einen perfekten Erstlauf.

## 1. Daten vorbereiten

Ziel: saubere Paare aus Kundenanfrage und Supportantwort importieren.

- Eingabeformat: CSV oder JSON mit `ticket_id`, `message_group_id`, `message`, `answer`.
- `message` sollte die Kundenfrage enthalten, `answer` die tatsächlich passende Antwort.
- Dubletten und sehr technische Systemtexte vorher reduzieren, wenn sie die Fachthemen überdecken.
- Zeilenumbrüche beim Import entfernen/ersetzen, wenn sie aus Copy/Paste, HTML oder E-Mail-Quoting stammen; erhalten, wenn sie fachlich Bedeutung tragen.

Faustregeln:

- Unter 100 Datensätzen: Ergebnisse eher als Sichtung/Proof-of-Concept lesen.
- 100-2.000 Datensätze: gut für manuelle Analyse und erste FAQ-Struktur.
- Über 2.000 Datensätze: zuerst grob clustern, danach relevante Cluster-Sets verfeinern.

## 2. Provider und Embeddings wählen

Ziel: semantisch brauchbare Vektoren erzeugen.

- Lokale Anbieter wie Ollama bevorzugen, wenn Datenschutz oder Offline-Arbeit wichtig ist.
- OpenAI bevorzugen, wenn Qualität und Robustheit wichtiger als lokale Ausführung sind.
- Für konsistente Vergleiche immer denselben Embedding-Provider und dasselbe Modell innerhalb einer Analyse verwenden.

Faustregeln:

- Erstlauf: ein solides allgemeines Embedding-Modell nutzen, keine Modellvergleiche parallel starten.
- Wenn Cluster fachlich unklar wirken: erst Parameter anpassen, dann Modell wechseln.
- Wenn Fragen und Antworten sehr unterschiedliche Sprache/Stil haben, später auch `answer` oder `combined` als Vektorbasis testen.

## 3. Indizierung starten

Ziel: alle importierten Paare mit Embeddings versehen.

Faustregeln:

- Für den ersten Datensatzlauf keine Spezialparameter ändern.
- Nach der Indizierung kurz prüfen, ob der Lauf vollständig abgeschlossen ist.
- Wenn Providerfehler auftreten: zuerst Provider-Verbindung und Modellliste prüfen, dann neu indizieren.

## 4. Erstes Cluster-Set erzeugen

Ziel: eine grobe Themenlandkarte bekommen.

Empfohlener Start:

| Parameter | Startwert | Wann ändern? |
| --- | --- | --- |
| Vektorbasis | `message` | Wenn du primär Kundenfragen zu FAQs bündeln willst. |
| Algorithmus | HDBSCAN | Wenn du natürliche, variable Clustergrößen erwartest. |
| Backend | `auto` | Standard; nutzt verfügbare Beschleunigung und fällt sonst auf CPU zurück. |
| Reduktion | `none` oder PCA | `none` für kleine/mittlere Daten; PCA bei vielen Daten oder sehr hohen Dimensionen. |
| `min_cluster_size` | ca. 2-5% der Datensätze, mindestens 5 | Größer = weniger, gröbere Cluster. Kleiner = mehr, feinere Cluster. |
| `min_samples` | leer oder ca. 10-20 | Größer = konservativer, mehr Ausreißer. Kleiner = mehr Zuordnungen. |
| `cluster_selection_epsilon` | `0.0` bis `0.1` | Erhöhen, wenn zu viele sehr ähnliche Kleincluster entstehen. |
| Summary-Beispiele | 10 | Für langsame lokale LLMs 3-8; für präzisere Summaries 10-20. |

### PCA/UMAP-Dimensionen

Der Default `10` ist bewusst ein schneller Grobscan-Wert. Er ist oft brauchbar, um eine erste Themenlandkarte zu erzeugen, kann aber semantische Feinheiten wegwerfen. Für ernsthafte Analyse sind `50` oder `100` häufig plausibler, sofern Laufzeit und Speicher passen.

Faustregeln:

- `10` Dimensionen: sehr grob, schnell, gut für erste Sichtung oder langsame lokale Läufe.
- `25-50` Dimensionen: guter Startbereich für viele Support-Datensätze.
- `100` Dimensionen: sinnvoll, wenn feinere semantische Unterschiede erhalten bleiben sollen.
- `200+` Dimensionen: nur bei großen Datensätzen oder wenn `50-100` sichtbar zu grob clustert.

| Datensätze | PCA-Dimensionen | UMAP-Dimensionen | Empfehlung |
| --- | ---: | ---: | --- |
| < 500 | 10-25 | 10-25 | Reduktion meist nur für schnelle Experimente nötig. |
| 500-2.000 | 25-50 | 25-50 | Guter Startbereich für normale Support-Analysen. |
| 2.000-10.000 | 50-100 | 25-75 | PCA `50` starten, bei zu groben Clustern auf `100`. |
| > 10.000 | 75-150 | 50-100 | Erst grob clustern, danach Child-Cluster-Sets verfeinern. |

PCA ist der stabilere erste Versuch: schneller, deterministischer und weniger verzerrend. UMAP kann Nachbarschaften stärker formen und Cluster sichtbarer trennen, kann aber auch künstliche Trennungen erzeugen. Deshalb: erst ohne Reduktion oder mit PCA testen; UMAP nur gezielt vergleichen.

Datensatzgrößen als grobe Orientierung:

| Datensätze | `min_cluster_size` | `min_samples` | Ziel |
| --- | ---: | ---: | --- |
| 50-200 | 3-8 | leer oder 5 | Kleine Themen sichtbar machen. |
| 200-1.000 | 10-40 | 10-20 | Gute erste Themenlandkarte. |
| 1.000-10.000 | 50-300 | 20-50 | Grobe Themen statt Detailcluster. |
| >10.000 | 2-5% | 30-100 | Erst grob, dann Child-Cluster-Sets verfeinern. |

## 5. Ergebnisse im Explorer lesen

Ziel: erkennen, welche Cluster fachlich verwendbar sind.

- `Score`: durchschnittliche Zuordnungsstärke der Quellen im Cluster. Höher ist stabiler; nur innerhalb desselben Cluster-Sets vergleichen.
- `Q/A-Mismatch`: semantische Distanz zwischen Kundenfrage und Supportantwort. Ab ca. `0.35` wird gewarnt; dann Quellen prüfen.
- `Ausreißer`: vom Algorithmus als Randfall erkannt. Nicht automatisch falsch, aber oft nicht FAQ-tauglich.
- `Status`: manueller Kurationsstatus. `rejected` schließt den Cluster aus der Standardansicht und aus Verfeinerungsquellen aus; `reviewed`, `in_progress`, `unreviewed` sind Workflow-Markierungen.

Faustregeln:

- Hoher Score, kein Q/A-Mismatch: zuerst als Kandidat für FAQ/Export prüfen.
- Niedriger Score, hoher Q/A-Mismatch: Quellen ansehen, oft Kandidat für Ausschluss oder Verfeinerung.
- Viele gute Cluster mit zu breiten Themen: Child-Cluster-Set aus eingeschlossenen Clustern erstellen.
- Viele irrelevante Cluster: als `rejected` markieren, dann mit den eingeschlossenen Clustern weiterarbeiten.

## 6. Summaries erzeugen

Ziel: pro Cluster eine kanonische Frage und Antwort erhalten.

Faustregeln:

- Lokale kleine LLMs: 3-8 Beispiele je Cluster, um Timeouts zu reduzieren.
- OpenAI oder stärkere lokale Modelle: 10-20 Beispiele je Cluster.
- `Alle Beispiele` nur bei kleinen Clustern oder wenn das Modell schnell genug ist.
- Nach Summary-Erstellung immer 5-10 Stichproben über „Quellen anzeigen“ prüfen.

Wenn Summaries zu generisch sind:

- Mehr Beispiele je Cluster verwenden.
- Cluster vorher verfeinern.
- Vektorbasis `message` nutzen, wenn die Fragen wichtiger sind.

Wenn Summaries falsche Antworten enthalten:

- Q/A-Mismatch-Cluster prüfen.
- Schlechte historische Antwortpaare ausschließen.
- Vektorbasis `answer` oder `combined` testen.

## 7. Iterieren

Ziel: von einer groben Themenkarte zu einer kuratierten Wissensbasis kommen.

Typischer Ablauf:

1. Grobes Root-Cluster-Set erstellen.
2. Im Explorer suchen, filtern, Quellen prüfen.
3. Irrelevante Cluster als `rejected` markieren.
4. „Eingeschlossene Cluster verfeinern“ verwenden.
5. Parameter für das Child-Cluster-Set feiner setzen.
6. Summaries neu erstellen.
7. Exportieren.

Parameter-Tuning:

- Zu viele Cluster: `min_cluster_size` erhöhen, danach `cluster_selection_epsilon` auf `0.1-0.2`.
- Zu wenige/grobe Cluster: `min_cluster_size` senken, `epsilon` Richtung `0.0`.
- Zu viele Ausreißer: `min_samples` senken oder `outlier_threshold` weglassen/senken.
- Zu wenige Ausreißer: `min_samples` erhöhen oder `outlier_threshold` vorsichtig setzen.
- Themen nach Antworten statt Fragen gruppiert: Vektorbasis `answer`.
- Fragen und Antworten gemeinsam berücksichtigen: Vektorbasis `combined`, Startgewicht `message=0.7`, `answer=0.3`; bei Antwortlogik `0.5/0.5`.

## 8. Export

Ziel: den aktuellen Arbeitsstand reproduzierbar sichern.

- Vor dem Export Such-/Filterzustand bewusst setzen.
- Ausgeschlossene Cluster nur anzeigen/exportieren, wenn sie Teil der Review-Dokumentation sein sollen.
- CSV für Tabellenarbeit; JSON für Weiterverarbeitung oder technische Übergaben.

Faustregel: Erst exportieren, wenn die wichtigsten Cluster `reviewed` oder bewusst `rejected` sind und die Summary-Stichprobe plausibel ist.
