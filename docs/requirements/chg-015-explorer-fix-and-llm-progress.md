# Explorer-Fixierung und sichtbarer LLM-Fortschritt

- Requirement ID: chg-015-explorer-fix-and-llm-progress
- Status: implemented
- Ready for implementation: yes
- Decision owner: mawi
- Last updated: 2026-08-16

## Problem

Fixieren ist im Explorer nur über das Statusfeld erreichbar. Außerdem bleibt der
Fortschritt von `llm_taxonomy` während des blockierenden Provideraufrufs bei 60 %
stehen und springt anschließend fast unmittelbar auf 100 %.

## Desired outcome

Jede Explorer-Zeile bietet neben Ausschließen eine direkte, umkehrbare
Fixieraktion. Während einer länger laufenden LLM-Taxonomiekonsolidierung bewegt sich
der bestehende Fortschrittsbalken monoton und begrenzt weiter. Da der Provider keine
Teilfortschritte meldet, ist dieser Zwischenstand ausdrücklich eine Zeitschätzung;
Persistenz und Abschluss bleiben echte Phasengrenzen.

## Acceptance criteria

- [x] AC-1: Neben „Ausschließen“ zeigt jede Explorer-Zeile „Fixieren“; bei einem
  fixierten Cluster heißt dieselbe Aktion „Fixierung aufheben“.
- [x] AC-2: Fixieren setzt `manual_status=fixed`; Aufheben entfernt den manuellen
  Status und stellt den effektiven automatischen Status wieder her.
- [x] AC-3: Erfolg und Fehler verwenden die bestehende Feedback-/PATCH-Logik, zeigen
  keinen falschen Erfolg und lassen die aktuelle Zeile bei Fehler unverändert.
- [x] AC-4: Während eines blockierenden `llm_taxonomy`-Provideraufrufs steigt der
  Fortschritt zeitbasiert monoton von 60 % bis höchstens 74 %; 75 % bleibt der
  Persistenz vorbehalten und 100 % dem abgeschlossenen Job.
- [x] AC-5: Die Schätzung endet auch bei Providerfehlern zuverlässig und erzeugt
  keine unbeschränkten Threads, Datenbankupdates oder Inhaltslogs.
- [x] AC-6: Desktop- und Mobile-Evidenz belegt die direkte Fixieraktion und einen
  laufenden Taxonomie-Zwischenstand im bestehenden Layout.
- [x] AC-7: Fokussierte Tests, Full Verify sowie unabhängiger Code-/Security- und
  Visual-Review sind grün.
