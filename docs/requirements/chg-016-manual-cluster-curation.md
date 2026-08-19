# Manuelle Cluster-Kuration und direkte Explorer-Bearbeitung

- Requirement ID: chg-016-manual-cluster-curation
- Status: draft
- Ready for implementation: no
- Decision owner: mawi
- Last updated: 2026-08-19

## Problem

Der Explorer kann vorhandene Cluster teilweise korrigieren, aber keine fehlenden
Cluster anlegen. FAQ-Frage und FAQ-Antwort sind nicht direkt bearbeitbar. Einzelne
Nachrichten können nicht aus einem Cluster in die Ausreißer verschoben werden. Ein
einzelner Cluster kann nicht gezielt durch das LLM aktualisiert werden, und Quellen
können nicht als Referenzen für eine bereichsbezogene Ähnlichkeitssuche dienen.

## Desired outcome

Im Explorer kann ein Analyst entweder ein leeres manuelles Cluster mit Titel,
Kategorie, FAQ-Frage und FAQ-Antwort anlegen oder mindestens ein Beispiel angeben.
Im zweiten Fall erzeugt ein konfiguriertes LLM die vier Startfelder. Optional werden
ähnliche Nachrichten anhand der gewählten Nachrichten-/Antwortbasis gesucht und
nach Bestätigung dem neuen Cluster zugewiesen.

Titel, Kategorie, FAQ-Frage, FAQ-Antwort und Status bestehender Cluster werden direkt
im Explorer ohne separaten Speichern-Button bearbeitet und automatisch gespeichert.
Eine einzelne Quelle kann aus einem Cluster entfernt und in den Ausreißer-Cluster
verschoben werden. Ein einzelner Cluster kann im Explorer per LLM neu zusammengefasst
werden. Im Quellen-Dialog können eine oder mehrere Quellen als Referenzen markiert
werden; danach sucht der Explorer anhand von Kundennachricht oder Supportantwort im
gewählten Bereich nach ähnlichen Nachrichten.

## Acceptance criteria

- [ ] AC-1: Ein leeres manuelles Cluster kann nur mit nichtleeren Titel-, Kategorie-,
  FAQ-Frage- und FAQ-Antwortwerten angelegt werden.
- [ ] AC-2: Bei mindestens einem gültigen Beispiel kann das LLM Titel, Kategorie,
  FAQ-Frage und FAQ-Antwort als strukturierte Startwerte erzeugen; Provider-, Modell-
  und OpenAI-Bestätigung folgen den bestehenden Regeln.
- [ ] AC-3: Ähnliche Nachrichten können anhand von Kundennachricht oder
  Supportantwort gesucht werden. Der Suchbereich unterscheidet diesen Cluster,
  alle Cluster des geladenen Sets, alle aktiven Paare und nur Ausreißer eindeutig.
- [ ] AC-4: Suchtreffer werden mit Ähnlichkeitswert, bisherigem Cluster und
  Ausreißerstatus als Vorschau angezeigt und erst nach Bestätigung zugewiesen.
- [ ] AC-5: Manuelle Cluster und Membership-Änderungen erhalten die
  Cluster-Set-Historie; automatisch erzeugte Cluster-Sets bleiben unverändert.
- [ ] AC-6: Titel, Kategorie, FAQ-Frage, FAQ-Antwort und Status werden inline ohne
  Speichern-Button gespeichert. Fehler rollen die jeweilige Änderung sicher zurück
  und zeigen keinen falschen Erfolg.
- [ ] AC-7: „Quellen anzeigen“ bietet je Quelle eine Aktion zum Verschieben in die
  Ausreißer. Die Quelle verschwindet erst nach erfolgreicher Transaktion aus dem
  Ursprungscluster und bleibt nachvollziehbar als manuelle Ausreißer-Zuordnung.
- [ ] AC-8: Jede Änderung ist projektbezogen autorisiert, transaktional,
  wiederholbar sicher und gegen konkurrierende Änderungen geschützt.
- [ ] AC-9: Originaltexte, LLM-Prompts/-Antworten und vollständige ID-Listen werden
  nicht in Logs oder Problem Details ausgegeben; Eingaben und UI-Zustände bleiben
  bei recoverbaren Fehlern erhalten.
- [ ] AC-10: Backend-, API-, Frontend-, Migrations-, Sicherheits-,
  Accessibility- und unabhängige visuelle Prüfungen sind erfolgreich.
- [ ] AC-11: Ein einzelner Cluster kann im Explorer mit einem ausgewählten LLM-
  Provider/Modell aktualisiert werden. Nur Titel, Kategorie, FAQ-Frage und
  FAQ-Antwort dieses Clusters ändern sich; Memberships und andere Cluster bleiben
  unverändert.
- [ ] AC-12: Im Quellen-Dialog können eine oder mehrere Quellen als Referenzen
  ausgewählt werden. Die Suche akzeptiert Kundennachricht oder Supportantwort und
  die Bereiche „dieser Cluster“, „alle Cluster“, „alle aktiven“ und „nur Ausreißer“.
- [ ] AC-13: Referenzsuchtreffer zeigen Ähnlichkeitswert, Quelle, aktuellen Cluster
  und Status. Die Suche führt nicht ohne ausdrückliche Bestätigung zu einer
  Membership-Änderung und kann für die manuelle Clustererstellung übernommen werden.

## Open decisions

- D001: Der empfohlene Lifecycle ist ein mutierbarer `manual_edit`-Child-Cluster-Set,
  der beim ersten strukturellen Edit aus dem geladenen Set entsteht. Dadurch bleiben
  generierte Sets unverändert und mehrere einzelne Quellen können ohne lineare
  Child-Kette entfernt werden. Dies erfordert die ausdrückliche Freigabe, dass nur
  `manual_edit`-Child-Sets Memberships ändern dürfen.
- D002: Als Beispiel ist zunächst eingegebener Text für Nachricht oder Antwort
  vorgesehen; bestehende Quellen als direkt übernehmbare Beispiele bleiben eine
  optionale spätere Ergonomie.
- D003: Die Ähnlichkeit nutzt persistierte Embeddings des gewählten Indexierungsruns
  und Cosine-Ähnlichkeit; bei Freitext wird derselbe Embedding-Provider/-Modellpfad
  verwendet. Kein `SequenceMatcher` als Primärlogik.
- D004: „Alle Cluster“ umfasst alle Cluster des geladenen Cluster-Sets einschließlich
  abgelehnter und Ausreißer; „alle aktiven“ schließt effektiven Status `rejected` aus.
- D005: Explizite Auswahl eines vorhandenen LLM-Providers und Modells bleibt für
  Erzeugung und Einzel-Cluster-Aktualisierung erforderlich; OpenAI verlangt die
  bestehende Cloud-Bestätigung.
- D006: LLM-Werte sind Startwerte und werden nach Erstellung oder Aktualisierung über
  dieselben Inline-Overrides editierbar.
- D007: Eine einzelne Cluster-LLM-Aktualisierung nutzt denselben bestehenden Summary-
  Providerpfad wie die Cluster-Set-Summary-Regeneration, aber mit genau einem Cluster
  und bounded Quellen-Sample. Memberships bleiben unverändert.
- D008: Referenzsuche wird im Quellen-Dialog gestartet. Die Auswahl einer oder
  mehrerer Quellen wird an die Explorer-Suche übergeben.
- D009: Bei mehreren Referenzen wird als empfohlene Aggregation je Kandidat die
  höchste Ähnlichkeit zu einer Referenz verwendet. Das findet Varianten wieder,
  ohne unterschiedliche Referenzintentionen durch einen Mittelwert zu verwischen.
- D010: Die vier Suchbereiche sind dieser Cluster, alle Cluster des geladenen Sets,
  alle aktiven Paare und nur Ausreißer.
- D011: Referenzsuche ist zunächst Vorschau/Selektion. Eine Zuweisung erfolgt nur
  über den bestehenden manuellen Cluster-Commit und nie automatisch durch die Suche.

## Readiness decision

- Shared understanding confirmed: no
- Impact analysis accepted: no
- Ready for implementation: no
- Remaining blockers: D001–D011 sowie genehmigter Design-Delta für Klasse 2.
