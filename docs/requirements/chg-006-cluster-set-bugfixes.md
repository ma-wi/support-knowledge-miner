# Cluster-Set Bugfixes nach Batch-Verfeinerung

- Requirement ID: chg-006-cluster-set-bugfixes
- Status: implemented
- Decision owner: mawi
- Last updated: 2026-08-09

## Problem

Nach der Cluster-Set Batch-Verfeinerung sind mehrere Bedien- und
Verhaltensfehler sichtbar: Duplizieren berechnet ein Cluster-Set neu statt es zu
klonen, Agglomerative-Parameter mit leerem Gegenfeld werden serverseitig falsch
abgelehnt, Löschaktion und Explorer-Auswahl sind missverständlich, und Explorer
Metadaten zeigen keine ausreichende Status-/Volumenaufschlüsselung.

## Desired outcome

Cluster-Set-Duplizieren erzeugt eine vollständige Kopie des ausgewählten Sets mit
Clustern, Mitgliedschaften, Kurationsstatus und Metadaten ohne Neuberechnung.
Agglomerative akzeptiert genau die gewählte Schnittregel. Die Cluster-Set-
Übersicht nutzt eine eindeutige Aktion “Löschen”. Der Explorer zeigt keine
redundante Cluster-Set-Auswahl oben rechts und zeigt Status- und
Nachrichtenpaar-Zusammenfassungen.

## Acceptance criteria

- [x] AC-1: “Duplizieren” klont ein abgeschlossenes Cluster-Set 1:1 inklusive
  Cluster, Mitgliedschaften, effektiver Status-/Titel-/Kategorie-Kuration,
  Ausreißerkennzeichnung, Parameter, LLM-Metadaten und Parent-Ebene; es wird kein
  Cluster-Job gestartet.
- [x] AC-2: Ein Duplikat dupliziert weiterhin keine Child-Cluster-Sets.
- [x] AC-3: Agglomerative mit `distance_threshold` sendet/akzeptiert kein
  `n_clusters: null`; Agglomerative mit `n_clusters` sendet/akzeptiert kein
  `distance_threshold: null`.
- [x] AC-4: Die Cluster-Set-Übersicht zeigt statt “Auswahl löschen” ein
  Aktionsmenü “Aktionen” mit der Aktion “Löschen”.
- [x] AC-5: Der redundante Explorer-Button “Cluster-Set auswählen” ist entfernt.
- [x] AC-6: Explorer-Metadaten zeigen Gesamtcluster, nicht abgelehnte Cluster,
  rejected Cluster, Anzahl je Status und Nachrichtenpaar-Anzahl je Status.
- [x] AC-7: Fehlerfälle bleiben safe und zeigen keinen rohen Trace oder
  Produktions-/Datenbankdetail.
- [x] AC-8: Das Infofeld „Verfeinerung vorausgefüllt“ zeigt das zu
  verfeinernde Cluster-Set und die ausgewählten Quellcluster-Namen sichtbar an.
- [x] AC-9: Cluster-Set-Start erzeugt keinen internen Serverfehler durch
  fehlerhafte `cluster_sets`-Insert-Parameter.
