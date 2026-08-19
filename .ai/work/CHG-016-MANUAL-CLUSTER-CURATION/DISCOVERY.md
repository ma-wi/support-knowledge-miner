# Feature discovery: Manuelle Cluster-Kuration und direkte Explorer-Bearbeitung

- Requirement ID: chg-016-manual-cluster-curation
- Status: awaiting-confirmation
- Facilitator/agent: Codex
- Decision owner: mawi
- Last updated: 2026-08-19

## Discovery trigger

Die gewünschte Bedienung umfasst gleichzeitig neue Cluster, LLM-generierte
Metadaten, gezielte Einzel-Cluster-Summaries, referenzbasierte Ähnlichkeitssuche,
Membership-Verschiebungen und direkte Autospeicherung.
Die bestehende Architektur schützt jedoch die Unveränderlichkeit erzeugter
Cluster-Sets. Besonders der Lifecycle manueller Membership-Änderungen kann die
Datenhistorie, API und UX materiell verändern.

## Current shared-understanding summary

Der Analyst soll im Explorer fehlende fachliche Cluster selbst ergänzen können.
Ohne Beispiel werden die vier FAQ-Felder manuell eingegeben; mit mindestens einem
Beispiel soll ein LLM sie erzeugen. Ähnliche Nachrichten sollen als überprüfbare
Vorschau gefunden und anschließend dem neuen Cluster zugewiesen werden. Bestehende
Clusterfelder und Status sollen inline automatisch gespeichert werden. Quellen sollen
einzeln in die Ausreißer verschoben werden. Der Analyst soll eine oder mehrere
Quellen als Referenzen markieren und in einem klaren Bereich nach ähnlichen
Nachrichten suchen können.

## Decision tree

| ID | Decision or question | Depends on | Recommended answer | User decision | Status |
|---|---|---|---|---|---|
| D001 | Wie werden strukturelle Membership-Änderungen gespeichert? | none | Beim ersten Edit aus dem geladenen Set einen `manual_edit`-Child erzeugen; dieser darf danach in-place kuratiert werden. Generierte Sets bleiben unveränderlich. |  | recommended |
| D002 | Was ist ein Beispiel in der ersten Ausbaustufe? | none | Ein oder mehrere eingegebene Texte, jeweils als Kundennachricht oder Supportantwort; bestehende Quelle als Beispiel später. |  | recommended |
| D003 | Wie wird die Ähnlichkeit berechnet? | D002 | Persistierte Embeddings des gewählten Indexierungsruns und Cosine-Ähnlichkeit; bei Freitext wird derselbe Embedding-Provider/-Modellpfad verwendet. Kein `SequenceMatcher` als Primärlogik. |  | recommended |
| D004 | Welche Quellen umfasst „alle Cluster“? | none | Alle Cluster des geladenen Cluster-Sets einschließlich abgelehnter und Ausreißer; „alle aktiven“ schließt nur effektiven Status `rejected` aus. |  | recommended |
| D005 | Wie wird das LLM ausgewählt? | D002 | Explizite Auswahl eines vorhandenen LLM-Providers und Modells für Erzeugung und Einzel-Refresh; OpenAI verlangt die bestehende Cloud-Bestätigung. |  | recommended |
| D006 | Werden LLM-Felder vor dem Anlegen noch korrigierbar? | D002 | Ja. LLM-Werte sind Startwerte und werden nach Erstellung über dieselben Inline-Overrides editierbar. |  | recommended |
| D007 | Wie wird ein einzelner Cluster aktualisiert? | none | Bestehenden Summary-Pfad wiederverwenden, aber genau einen Cluster mit bounded Sample aktualisieren; Memberships bleiben unverändert. |  | recommended |
| D008 | Wo werden Referenzen ausgewählt? | none | Im bestehenden Quellen-Dialog; eine oder mehrere Quellen markieren und danach die Suche öffnen. |  | recommended |
| D009 | Wie werden mehrere Referenzen aggregiert? | D008 | Kandidatenscore ist das Maximum der Cosine-Ähnlichkeiten zu den ausgewählten Referenzen. |  | recommended |
| D010 | Was bedeuten die Suchbereiche? | D008 | Dieser Cluster; alle Cluster des geladenen Sets; alle aktiven (`effectiveStatus != rejected`); nur Ausreißer. |  | recommended |
| D011 | Ändert die Suche direkt Memberships? | D008 | Nein. Sie liefert Vorschau/Selektion; Übernahme erfolgt ausschließlich über den bestätigten manuellen Cluster-Commit. |  | recommended |

## Recommended interview order

1. D001 Lifecycle und Änderbarkeit des `manual_edit`-Child-Sets bestätigen.
2. D002 Eingabeform der Beispiele bestätigen.
3. D003–D011 als empfohlene Folgeentscheidungen bestätigen oder ändern.
4. Danach Design-Delta und Plan auf `ready-for-implementation` heben.

## Confirmed decisions

- Noch keine.

## Rejected alternatives

- `SequenceMatcher` als primäre Ähnlichkeit: semantische Paraphrasen werden nicht
  zuverlässig erkannt und die Anwendung besitzt bereits passende Embeddings.
- Zweite parallele Membership-Tabelle: widerspricht der bestehenden Verantwortung
  von `cluster_memberships` und der Eindeutigkeitsinvariante pro Cluster-Set.
- Direkte Mutation automatisch erzeugter Cluster-Sets: würde die akzeptierte
  Cluster-Set-Historie und Vergleichbarkeit brechen.

## Assumptions accepted for planning

- Alle Aktionen bleiben projekt- und sessionspezifisch; Produktionszugriff ist nicht
  Bestandteil.
- Die vorhandene Cluster-/Provider-Service-Verantwortung wird erweitert.
- Bestehende automatische Cluster- und Summary-Felder bleiben aus
  Rückwärtskompatibilitätsgründen erhalten; manuelle FAQ-Overrides kommen ergänzend.

## Open questions and blockers

- D001–D011 benötigen die Bestätigung des Entscheidungseigners.
- Die konkrete visuelle Richtung für den neuen mehrstufigen Erstellungsfluss ist im
  Design-Delta vorgeschlagen, aber noch nicht genehmigt.

## Proposed scope

### In scope

- Manuelles leeres oder beispielbasiertes Cluster.
- Einzel-Cluster-LLM-Aktualisierung für Titel, Kategorie und beide FAQ-Felder.
- Semantische Treffer-Vorschau und bestätigte manuelle Zuordnung.
- Referenzauswahl im Quellen-Dialog mit vier Suchbereichen und zwei Suchbasen.
- Inline-Autosave für Titel, Kategorie, FAQ-Frage, FAQ-Antwort und Status.
- Einzelnes Verschieben einer Quelle in den Ausreißer-Cluster.
- Persistenz, API, Fehlerkatalog, Tests, Spezifikation und UI-Qualitätsnachweis.

### Out of scope / non-goals

- Freie Bearbeitung automatischer Memberships in automatisch erzeugten Sets.
- Neue externe Such- oder Fuzzy-Matching-Abhängigkeit.
- Automatische fachliche Freigabe einer FAQ.
- Freie Membership-Änderung allein durch das Öffnen oder Ausführen der Referenzsuche.

## Draft success and acceptance criteria

- [ ] Die dreizehn Kriterien in `docs/requirements/chg-016-manual-cluster-curation.md`
  sind mit den bestätigten D001–D011 konsistent.

## Shared-understanding confirmation

Vor Implementierungsbereitschaft muss der Entscheidungseigner die Zusammenfassung,
die D001–D011, den Umfang und die Annahmen bestätigen.

- User explicitly confirmed shared understanding: no
- Confirmed by:
- Confirmation date:
- Corrections or conditions:
