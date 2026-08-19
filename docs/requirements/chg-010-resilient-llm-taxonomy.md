# Robuste LLM-Taxonomie-Konsolidierung

- Requirement ID: chg-010-resilient-llm-taxonomy
- Status: implemented
- Decision owner: mawi
- Last updated: 2026-08-15

## Problem

Ein vollständiger Structured-Output kann die Taxonomie derzeit trotzdem komplett
scheitern lassen, wenn das LLM Quell-Cluster-IDs auslässt, doppelt verwendet,
unbekannte IDs liefert oder Summary-Felder länger als die internen Speichergrenzen
formuliert. Ein einzelner semantischer Zuordnungsfehler verwirft damit den gesamten
Job. Zusätzlich begrenzt die Anwendung Taxonomieausgaben auf 16.000 Tokens, obwohl
das konkret verwendete Modell deutlich größere strukturierte Ausgaben unterstützt.

## Desired outcome

Eine formal gültige Taxonomieantwort wird deterministisch zu einer vollständigen,
eindeutigen Partition normalisiert. Gültige Zuordnungen bleiben erhalten;
doppelte und unbekannte Zuordnungen werden verworfen; fehlende Quellcluster werden
verlustfrei als eigene Zielcluster aus ihrer bestehenden Summary übernommen.
Zu lange generierte Summary-Felder werden sicher normalisiert statt den Job zu
verwerfen. Das Taxonomie-Ausgabebudget nutzt die dokumentierte Modellkapazität und
bleibt lediglich durch feste Ressourcen-Hard-Caps gebunden.

## Acceptance criteria

- [x] AC-1: Fehlende, doppelte und unbekannte Quell-IDs führen nicht mehr zum
  Fehlschlag; das persistierte Ergebnis enthält jede erwartete Quell-ID exakt einmal.
- [x] AC-2: Fehlende Zuordnungen werden mit der bestehenden Quellsummary als eigener
  Zielcluster übernommen; keine Inhalte oder Memberships gehen verloren.
- [x] AC-3: Zu lange LLM-Titel, Kategoriepfade, Fragen und Antworten werden
  whitespace-normalisiert und an der bestehenden Feldgrenze gekürzt.
- [x] AC-4: Malformed JSON, falsche Root-/Objektstruktur, leere Antworten und
  Providerfehler bleiben sichere, retrybare Fehlschläge ohne False Success.
- [x] AC-5: Taxonomieaufrufe können bis zu 128.000 Output-Tokens und 1.000.000
  Antwortzeichen nutzen; andere LLM-Aktionen behalten ihre kleineren Defaults.
- [x] AC-6: Sichere Logs nennen Reparaturzähler, aber weder Inhalte noch vollständige
  ID-Listen.
- [x] AC-7: API, UI, Persistenzschema und bestehende erfolgreiche Taxonomien bleiben
  kompatibel.
