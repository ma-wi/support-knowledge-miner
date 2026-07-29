# Requirement: Sichtbarer Pending-Status bei der Clustererzeugung

- Requirement ID: CHG-003
- Work type: incremental-change
- Status: accepted
- Affected capability specification:
  `docs/specifications/support-knowledge-miner-mvp1.md`

## Problem

Die Clustererzeugung läuft über einen synchronen, potenziell lang dauernden
API-Aufruf. Nach dem Klick auf „Cluster erzeugen“ zeigt die Projektoberfläche bis
zur Antwort weder einen laufenden Zustand noch eine veränderte Schaltfläche. Der
Klick wirkt deshalb wirkungslos und kann erneut ausgelöst werden.

## Desired outcome

Die Oberfläche bestätigt den Start der Clustererzeugung unmittelbar, kennzeichnet
den betroffenen Run während des offenen Requests sichtbar als laufend und verhindert
eine erneute Clustererzeugung. Nach Erfolg oder Fehler endet der laufende Zustand;
die bestehende konkrete Erfolgs- beziehungsweise Fehlerrückmeldung bleibt erhalten.

## Invariants

- Die bestehende synchrone HTTP-Route und ihr JSON-Vertrag bleiben unverändert.
- Nur abgeschlossene Analyse-Runs können geclustert werden.
- Projektisolierung, serverseitige Budgetprüfung, Transaktionalität und sichere
  Fehlermeldungen bleiben unverändert.
- Ein verspätetes Ergebnis aus einem nicht mehr aktuellen Projektkontext darf den
  inzwischen geöffneten Projektzustand nicht überschreiben.

## Scope

### In scope

- Pending-Zustand und unmittelbare nicht-fehlerhafte Rückmeldung für die bestehende
  Aktion „Cluster erzeugen“.
- Schutz gegen wiederholte Auslösung während eines offenen Cluster-Requests.
- Frontend-Regressionstest mit kontrolliert offenem Request.

### Out of scope / non-goals

- Asynchroner Backend-Job, Fortschrittsprozent, Polling, SSE oder WebSockets.
- Änderung an Clustering-Algorithmen, API, Persistenz oder Ressourcenlimits.
- Allgemeine Überarbeitung aller Loading-Zustände.

## Acceptance criteria

- [x] AC-1: Unmittelbar nach dem Klick ist für den ausgewählten Run sichtbar, dass
  die Clustererzeugung läuft, auch solange der API-Request noch offen ist.
- [x] AC-2: Während dieses Requests kann keine weitere Clustererzeugung ausgelöst
  werden; mindestens die aktive Schaltfläche ist deaktiviert und eindeutig als
  laufend beschriftet.
- [x] AC-3: Nach Erfolg werden die Cluster wie bisher geladen und die
  Erfolgsmeldung angezeigt; nach einem sicheren API-Fehler wird dessen konkrete
  Meldung wie bisher als Fehler angezeigt. In beiden Fällen endet der Pending-State.
- [x] AC-4: Ein nach einem Projektwechsel eintreffendes Ergebnis verändert weder
  Cluster noch Feedback des neuen Projektkontexts.
- [x] AC-5: Fokussierte Frontend-Tests und `./.ai/tools/verify.sh` laufen
  erfolgreich; ein unabhängiger Review hat keine offenen P0/P1-Findings.

## Decision owner and approval

- Decision owner: anfordernder Product Owner (Conversation User; Name nicht
  angegeben)
- Shared understanding: confirmed 2026-07-28
- Approval status: accepted
