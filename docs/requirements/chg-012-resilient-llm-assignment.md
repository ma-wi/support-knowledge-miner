# Robuste LLM-Assignment-Zuordnung

- Requirement ID: chg-012-resilient-llm-assignment
- Status: implemented
- Ready for implementation: yes
- Decision owner: mawi
- Last updated: 2026-08-15

## Problem

Ein formal gültiger Assignment-Batch verwirft den gesamten Child-Job, sobald das
LLM eine Paar-ID auslässt, doppelt nennt, eine unbekannte Paar-ID zurückgibt oder
eine unbekannte Cluster-ID wählt. Beim aktuellen lokalen Job mit 23.801 Paaren und
41 effektiven Taxonomieclustern geschah dies bereits im ersten Batch.

## Desired outcome

Formal gültige Assignment-Antworten werden verlustfrei normalisiert: Die erste
gültige bekannte Zuordnung bleibt erhalten; unbekannte Paar-IDs und Duplikate werden
ignoriert; fehlende Paare sowie ungültige oder unbekannte Zielcluster landen im
gemeinsamen Ausreißer. Nur formal unbrauchbare Antworten und unvollständige
Parent-Summaries bleiben Fehler.

## Acceptance criteria

- [x] AC-1: Fehlende Batch-Paare werden als Ausreißer ergänzt.
- [x] AC-2: Für doppelte bekannte Paar-IDs gewinnt die erste Zuordnung; unbekannte
  Paar-IDs werden ignoriert.
- [x] AC-3: Ungültige oder unbekannte Zielcluster für ein erwartetes Paar werden als
  Ausreißer normalisiert.
- [x] AC-4: Das Ergebnis enthält jede erwartete Batch-Paar-ID exakt einmal.
- [x] AC-5: Falsche Root-/Objektstruktur, falsche Feldtypen, malformed JSON und
  fehlende Parent-Summaries bleiben sichere Fehlschläge ohne Teilpersistenz.
- [x] AC-6: Sichere Diagnostik loggt nur Cluster-Set-ID und aggregierte
  Reparaturzähler, keine Inhalte oder Paar-/Cluster-IDs.
- [x] AC-7: Fokussierte Tests, Full Verify und unabhängiger Code-/Security-Review
  sind grün.
