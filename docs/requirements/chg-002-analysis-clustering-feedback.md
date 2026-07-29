# Requirement: Transparente und performante Analyse- und Clusterläufe

- Requirement ID: CHG-002
- Work type: incremental-change
- Status: accepted
- Affected capability specifications:
  `docs/specifications/support-knowledge-miner-mvp1.md`,
  `docs/specifications/local-runtime-providers.md`

## Problem

Laufende Analysen zeigen nach dem Start dauerhaft 5 % und erst beim Abschluss
100 %. Der lokale Ollama-Standard entlädt das Modell nach jeder Anfrage, wodurch
aufeinanderfolgende Embedding-Batches wiederholte Ladezeiten verursachen.

Die Clustererzeugung kann bereits bei praktisch relevanten Datensätzen an der
512-MiB-Grenze scheitern, weil pgvector-Werte als Text und mehrere speicherteure
Python-Zwischenrepräsentationen materialisiert werden. Die UI verwirft dabei wie
auch in vielen anderen Fehlerpfaden die konkrete API-Fehlermeldung und zeigt jede
globale Statusmeldung im Erfolgsstil. Beim Laden einer leeren Clustermenge erhält
der Benutzer keine erklärende Rückmeldung.

## Desired outcome

Analyse-Runs zeigen einen monotonen, datenbasierten Fortschritt. Ein während eines
Runs verwendetes Ollama-Modell bleibt zwischen unmittelbar aufeinanderfolgenden
Embedding-Anfragen warm. Clustering nutzt eine native, speichereffiziente
Vektorrepräsentation und behält den verbindlichen 512-MiB-Schutz bei.

Jede fehlgeschlagene UI-Aktion zeigt die konkrete, sichere Backend-Fehlermeldung
oder bei nicht verfügbaren Details eine aktionsbezogene Netzwerk-/HTTP-Meldung.
Fehler sind visuell und semantisch als Fehler markiert. Leere Clusterergebnisse
werden ausdrücklich erklärt; nicht sinnvoll nutzbare Ladeaktionen sind deaktiviert.

## Users and stakeholders

- Analysten und Kuratoren in der lokalen Projektoberfläche.
- Lokaler Betreiber des Ollama-/PostgreSQL-Compose-Stacks.
- Decision owner: anfordernder Product Owner (Conversation User; Name nicht
  angegeben).

## Functional requirements

- FR-1: Ein laufender Analyse-Run aktualisiert `progress` nach erfolgreich
  verarbeiteten Nachrichten-Batches monoton zwischen Start- und Abschlusswert.
- FR-2: `completed` endet bei 100 %. Ein fehlgeschlagener Run behält den zuletzt
  erreichten Fortschritt; 100 % darf keinen erfolgreichen Abschluss vortäuschen.
- FR-3: Ollama-Embedding-Anfragen setzen eine begrenzte Keep-alive-Dauer, und der
  lokale Compose-Standard entlädt das Modell nicht zwischen den Batches eines
  normalen Runs.
- FR-4: Die bestehende Provider-/Modellwahl, Batchgrenze, Timeouts und
  No-Fallback-Regel bleiben unverändert.
- FR-5: Der Clustering-Pfad registriert den nativen pgvector-Psycopg-Typ und
  überführt Vektoren ohne Text-/Split-/Python-Float-Listen-Peak direkt in eine
  zusammenhängende numerische Arbeitsmatrix.
- FR-6: Die 512-MiB-Grenze wird anhand der tatsächlich gleichzeitig gehaltenen
  nativen Matrix-, Algorithmus- und Ergebnisrepräsentationen konservativ geprüft.
- FR-7: Eine weiterhin zu große Clusterung scheitert vor Cluster-Schreibzugriffen
  mit konkreten sicheren Angaben zu Datensatzgröße, Dimensionen, Schätzung und
  Grenzwert sowie einer handlungsorientierten Empfehlung.
- FR-8: Frontend-Fehlerpfade bewahren `ApiRequestError.message` und verwenden einen
  zentralen sicheren Fallback für Netzwerk-, HTTP- und unbekannte Fehler.
- FR-9: Globale Rückmeldungen besitzen einen Typ. Fehler verwenden sichtbare
  Fehlerfarben und `role="alert"`; nicht fehlerhafte Zustände verwenden
  `role="status"`.
- FR-10: „Cluster laden“ ist für nicht abgeschlossene Runs deaktiviert. Liefert ein
  abgeschlossener Run keine Cluster, zeigt die UI, dass zuerst Cluster erzeugt
  werden müssen; ein leerer erfolgreicher Abruf darf nicht still bleiben.

## Non-functional requirements

- Security/privacy: Keine Rückmeldung enthält Secrets, Rohtexte aus Supportdaten
  oder rohe Provider-Antworten. Bestehende serverseitige Sanitization bleibt
  maßgeblich.
- Performance: Wiederholtes Laden desselben Ollama-Modells zwischen
  aufeinanderfolgenden Run-Batches wird vermieden. Clustering darf keine
  vollständige paarweise Distanzmatrix erzeugen.
- Reliability: Fortschritt wird erst nach erfolgreicher Batchverarbeitung
  veröffentlicht und bleibt monoton. Fehlgeschlagene Clusterung schreibt keine
  partiellen Cluster.
- Accessibility: Fehler sind nicht allein über Farbe erkennbar, sondern zusätzlich
  über Live-Region-Semantik und Text.
- Compatibility: Bestehende HTTP-Routen und JSON-Feldnamen bleiben erhalten. Die
  Semantik von `progress` wird präzisiert; keine Datenmigration ist erforderlich.

## In scope

- Analyse-Fortschritt, Ollama-Warmhaltung und relevante Diagnosedaten.
- Native pgvector-Dekodierung und korrigierte Clustering-Speicherbudgetierung.
- Einheitliche sichere UI-Rückmeldungen in allen bestehenden Aktionsfehlerpfaden.
- Erklärter/gesperrter Cluster-Ladezustand.
- Automatisierte Regressionstests und Aktualisierung der beiden Spezifikationen
  sowie der lokalen Betriebsdokumentation.

## Out of scope / non-goals

- Aufhebung oder konfigurierbare Erhöhung der 512-MiB-Sicherheitsgrenze.
- Ein absoluter Laufzeit-SLA unabhängig von Modell, Hardware und Datenmenge.
- WebSockets/SSE, neue Status-Endpunkte oder ein neuer Jobdienst.
- Änderung von Clustering-Algorithmen oder deren fachlicher Ergebnisqualität.
- Produktionszugriff oder Tests mit Produktionsdaten.

## Acceptance criteria

- [x] AC-1: Ein Run mit mindestens drei Provider-Batches zeigt nach dem Start
  mindestens zwei monotone Zwischenstände größer 5 und kleiner 100; Abschluss ist
  100.
- [x] AC-2: Bei Fehler im späteren Batch bleibt der zuletzt bestätigte Fortschritt
  kleiner 100 erhalten und die konkrete sichere Run-Fehlermeldung sichtbar.
- [x] AC-3: Jede Ollama-Embedding-Anfrage enthält die akzeptierte begrenzte
  Keep-alive-Dauer; Compose-Beispiel und Standard halten das Modell zwischen
  normalen Batchanfragen warm.
- [x] AC-4: Ein nativer pgvector-Datensatz, der nur wegen der bisherigen
  Text-/Python-Zwischenrepräsentation über 512 MiB geschätzt wurde, erreicht den
  HDBSCAN-/Agglomerative-Testseam innerhalb des korrigierten Budgets.
- [x] AC-5: Eine tatsächlich über 512 MiB geschätzte Clusterung scheitert vor
  Cluster-Schreibzugriffen und zeigt in der UI die sichere konkrete API-Meldung.
- [x] AC-6: Alle bestehenden Frontend-Aktionsfehler verwenden die konkrete
  API-Meldung oder einen aktionsbezogenen sicheren Fallback und erscheinen
  semantisch sowie farblich als Fehler.
- [x] AC-7: „Cluster laden“ ist für nicht abgeschlossene Runs deaktiviert; ein leerer
  Abruf für einen abgeschlossenen Run erklärt sichtbar, dass noch keine Cluster
  erzeugt wurden.
- [x] AC-8: Bestehende Provider-Sicherheitsgrenzen, Transaktionsgarantien,
  Projektisolierung und Polling-Regeln bleiben durch Regressionstests erhalten.
- [x] AC-9: Fokussierte Tests, Dependency-/Security-Gates und
  `./.ai/tools/verify.sh` laufen erfolgreich; ein unabhängiger Review hat keine
  offenen P0/P1-Findings.

## Open questions

Keine. Der Decision Owner bestätigte fünf Minuten Ollama-Keep-alive, die
unveränderte 512-MiB-Grenze mit korrigierter Speichernutzung und konkrete,
serverseitig sicher bereinigte Fehlermeldungen.

## Approval

- Owner: anfordernder Product Owner (Conversation User; Name nicht angegeben)
- Status: accepted
- Date: 2026-07-28
