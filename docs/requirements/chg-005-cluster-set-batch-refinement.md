# Cluster-Set Batch-Verfeinerung und Agglomerative UI

- Requirement ID: chg-005-cluster-set-batch-refinement
- Status: accepted
- Decision owner: mawi
- Last updated: 2026-08-09

## Problem

Analysten können gute Parent-Cluster fachlich identifizieren, aber die bestehende
Verfeinerung clustert ausgewählte Quellen nur als eine gemeinsame Menge neu. Für
die gewünschte lokale Schärfung einzelner Parent-Cluster ist das unpräzise und
erzeugt hohen manuellen Aufwand. Zusätzlich ist Agglomerative zwar im Backend
vorhanden, aber im Cluster-Set-Formular nicht auswählbar.

## Desired outcome

Die Cluster-Set-Erzeugung unterstützt algorithmusspezifische UI-Parameter für
HDBSCAN und Agglomerative. Verfeinerungen können wahlweise gemeinsam oder separat
je ausgewähltem Parent-Cluster ausgeführt werden. Ein separater
Batch-Verfeinerungslauf erzeugt ein neues Child-Cluster-Set als
Durchlaufcontainer; darin behalten alle erzeugten Child-Cluster ihre eindeutige
Herkunft zum Parent-Cluster.

## Scope

In scope:

- Agglomerative im Frontend auswählbar machen.
- Algorithmusspezifische Parameterfelder anzeigen.
- Batch-Verfeinerungsmodus “separat je Parent-Cluster” planen.
- Cluster-Set-Übersicht um Mehrfachauswahl und Batch-Aktion Löschen erweitern.
- Cluster-Sets duplizieren, ohne Children zu duplizieren.
- Aktive Cluster- und Nachrichtenpaar-Anzahlen pro Cluster-Set anzeigen.
- Nach Cluster-Set-Erstellung zum eingefügten Set scrollen/fokussieren.
- Beim Verfeinern den Parent-Kontext sichtbar anzeigen, einschließlich der
  ausgewählten Parent-Cluster.
- LLM-Summary-Parameter in Cluster-Set-Metadaten anzeigen, insbesondere
  Beispielanzahl bzw. “alle Beispiele”.
- Umfangreiche Metadaten/Parameter im Cluster-Sets-Tab je Cluster-Set ein- und
  ausklappbar machen. Gemeint ist der Block unter dem Fortschrittsbalken bis vor
  den Aktionsbuttons: Phase/Basis/Algorithmus/Cluster, Parameterliste,
  Indizierung/Datensatz, Parent und LLM-Informationen.
- Parameterlabels robust kürzen/umbrechen; `cluster_selection_epsilon` in der UI
  kürzer als `selection_epsilon` anzeigen.
- Explorer-Cluster-Set-Auswahl mit sichtbarer Parent-/Child-Struktur anzeigen.
- Indizieren-Tab Layout-Bug bei vollem Fortschritt und langen Diagnoseparametern
  beheben.
- Klickbaren isolierten Mockup für Cluster-Sets und Explorer bereitstellen.

Out of scope:

- Produktionsimplementierung vor Mockup-/Planfreigabe.
- Automatische fachliche Benennung von Subclustern jenseits der bestehenden
  Summary-Funktion.
- Produktionszugriff oder externe Datenverbindungen.

## Acceptance criteria

- [x] AC-1: Im Cluster-Set-Formular kann HDBSCAN oder Agglomerative gewählt
  werden; nur passende Parameter sind sichtbar.
- [x] AC-2: PCA/UMAP-Reduktion und Backend-Auswahl erscheinen nur für HDBSCAN.
- [x] AC-3: Agglomerative kann mit `n_clusters` oder `distance_threshold` und
  `linkage` gestartet werden; `n_clusters` und `distance_threshold` sind in jedem
  Modus gegenseitig exklusiv und inkompatible Parameter werden nicht gesendet.
- [x] AC-4: Eine Verfeinerung kann als “gemeinsam neu clustern” oder “separat je
  Parent-Cluster verfeinern” gestartet werden.
- [x] AC-5: Ein separater Batch-Verfeinerungslauf erzeugt genau ein neues
  Child-Cluster-Set; die internen Clustering-Läufe schreiben Cluster in dieses
  eine Set und speichern pro Child-Cluster die Parent-Herkunft.
- [x] AC-6: Der Explorer kann Batch-Verfeinerungs-Ergebnisse nach Parent-Herkunft
  gruppieren und zeigt den Durchlauf im Analysepfad.
- [x] AC-7: Cluster-Set-Karten zeigen aktive Clusteranzahl und aktive
  Nachrichtenpaaranzahl, definiert als Cluster mit `effectiveStatus !== rejected`;
  Ausreißer zählen mit, solange sie nicht ausgeschlossen sind.
- [x] AC-8: Mehrere Cluster-Sets können in der Übersicht selektiert und per
  Batch-Aktion gelöscht werden.
- [x] AC-9: Ein Cluster-Set kann dupliziert werden; das Duplikat bleibt in der
  gleichen Ebene wie das Original und übernimmt keine Children.
- [x] AC-10: Nach “Cluster-Set erstellen” wird zum neu eingefügten Cluster-Set
  gescrollt und es ist visuell/fokusseitig auffindbar.
- [x] AC-11: Im Indizieren-Tab bleiben Fortschrittsbalken und Diagnoseparameter
  innerhalb der Karten-/Viewport-Breite und umbrechen bei langen Werten.
- [x] AC-12: Fehlerfälle verwenden sichere, catalogfähige Meldungen; fehlgeschlagene
  Aktionen zeigen keinen Erfolg und erhalten sichere Eingaben.
- [x] AC-13: Während einer Verfeinerung zeigt das Formular sichtbar den
  Parent-Cluster-Set-Namen und die ausgewählten Parent-Cluster.
- [x] AC-14: Cluster-Set-Parameterinfos zeigen LLM-Modell und
  LLM-Sample-Strategie, inklusive Beispielanzahl oder “alle Beispiele”.
- [x] AC-15: Der Metadatenblock jeder Cluster-Set-Karte im Cluster-Sets-Tab kann
  ein- und ausgeblendet werden; die Hauptzeile, Fortschritt und Aktionen bleiben
  sichtbar.
- [x] AC-16: Lange Parameterlabels und Werte überlappen nicht; das Label
  `cluster_selection_epsilon` wird als `selection_epsilon` angezeigt.
- [x] AC-17: Die Cluster-Set-Auswahl im Explorer zeigt die Parent-/Child-Struktur
  statt einer flachen Namensliste.

## Accepted decisions

- “Aktive/eingeschlossene Cluster” bedeutet `effectiveStatus !== rejected`.
  Ausreißer zählen mit, solange sie nicht ausgeschlossen/rejected sind.
- In diesem Change wird als mutierende Cluster-Set-Batch-Aktion nur Löschen
  geplant. “Parameter vergleichen” bleibt höchstens als spätere read-only
  Ergänzung außerhalb dieses Scopes.
- Parent-Herkunft wird zunächst in `clusters.metadata` gespeichert. Eine
  relationale Herkunftstabelle bleibt out of scope, solange keine globalen
  Herkunftsfilter oder Cross-Set-Reports erforderlich sind.
- Die zusätzliche Auswahl “Subcluster je Parent” wird nicht als eigenes Dropdown
  geplant. Stattdessen bekommt Agglomerative eine klare Schnittregel:
  `n_clusters`/`n_clusters je Parent` für feste Zielanzahl oder
  `distance_threshold`/`distance_threshold je Parent` für schwellenbasierte
  Clusteranzahl. Für HDBSCAN gibt es keinen Zielanzahl-Parameter.
- Der freigegebene Mockup ist eine Design-/Flow-Referenz für die Planung, kein
  Produktionscode. Die Umsetzung integriert die Entscheidungen in die bestehende
  produktive UI und darf bestehende relevante Controls nicht entfernen.
