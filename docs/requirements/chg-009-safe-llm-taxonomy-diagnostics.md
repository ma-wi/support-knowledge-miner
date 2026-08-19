# Sichere LLM-Taxonomie-Diagnostik

- Requirement ID: chg-009-safe-llm-taxonomy-diagnostics
- Status: superseded by `chg-010-resilient-llm-taxonomy`
- Decision owner: mawi
- Last updated: 2026-08-15

## Problem

> Die damalige 16.000-Token-Grenze und die strikte semantische Partitionsablehnung
> wurden durch `chg-010-resilient-llm-taxonomy` ersetzt. Dieses Dokument hält die
> frühere Owner-Entscheidung fest; die MVP-Spezifikation beschreibt den aktuellen
> Laufzeitvertrag.

Fehlgeschlagene LLM-Taxonomie-Jobs speichern derzeit nur die gemeinsame Meldung,
dass die LLM-Antwort ungültig war. Dadurch ist nicht erkennbar, ob die Antwort
abgeschnitten, formal ungültig oder wegen fehlender, doppelter beziehungsweise
unbekannter Quell-Cluster-IDs abgelehnt wurde.

## Desired outcome

Die lokale Backend-Ausgabe protokolliert für LLM-Taxonomie-Aufrufe ausschließlich
sichere Struktur- und Größenmetadaten. Sie nennt den konkreten Validierungsschritt,
ohne Prompttext, Summary-Felder, FAQ-Inhalte, Provider-Antwortkörper, Schlüssel oder
andere sensible Daten auszugeben.
Taxonomieaufrufe verwenden das vollständige sichere Ausgabebudget von 16.000 Tokens.
Eine vom Provider als unvollständig markierte Antwort wird nicht an den JSON-Parser
weitergereicht.

## Scope

- sichere Request-Metadaten: Cluster-Set, Provider-Typ, Modell, Anzahl Quellcluster,
  Promptlänge sowie Prompt-, Antwort- und Tokenbudget;
- sichere Response-Metadaten: Antwortlänge sowie Ergebnis- und ID-Anzahlen;
- konkrete Taxonomie-Ablehnungsgründe und nur aggregierte ID-Abweichungen;
- sichere OpenAI-Diagnostik für als `incomplete` markierte Antworten;
- 16.000 Ausgabetokens für jeden `llm_taxonomy`-Aufruf;
- unmittelbare sichere Providerfehlermeldung für unvollständige Antworten;
- Wiederherstellung der allgemeinen getesteten Hard-Caps von 500.000 Promptzeichen
  und 16.000 Ausgabetokens;
- automatische Tests, die insbesondere das Nicht-Protokollieren von Prompt- und
  Antwortinhalten beweisen.

## Non-goals

- Protokollierung vollständiger Prompts, Summaries oder LLM-Antworten;
- Änderung von API-, UI-, Persistenz- oder Fehlercodes;
- automatische Wiederholungs- oder Chunkinglogik.

## Acceptance criteria

- [x] AC-1: Jeder LLM-Taxonomie-Aufruf protokolliert sichere Request- und
  Response-Größen sowie die verwendeten Budgets in der lokalen Backend-Ausgabe.
- [x] AC-2: Eine abgelehnte Taxonomie protokolliert einen stabilen Grund und
  aggregierte erwartete, gelieferte, fehlende, doppelte und unbekannte ID-Anzahlen.
- [x] AC-3: Eine unvollständige OpenAI-Antwort protokolliert den sicheren
  Providergrund und ob Textfragmente vorhanden waren.
- [x] AC-4: Logs und persistierte Fehler enthalten weder Prompt-/Antwortinhalt noch
  Supporttexte, Provider-Antwortkörper, Zugangsdaten oder vollständige ID-Listen.
- [x] AC-5: Bestehende Fehlercodes, UI-Recovery, API-Verträge und erfolgreiche
  Taxonomieergebnisse bleiben kompatibel.
- [x] AC-6: `llm_taxonomy` fordert 16.000 Ausgabetokens an; der allgemeine Provider
  lehnt Werte über 16.000 Tokens und 500.000 Promptzeichen weiterhin ab.
- [x] AC-7: OpenAI-Antworten mit Status `incomplete` werden als
  `LLM_PROVIDER_UNAVAILABLE` beendet und niemals als partielle Taxonomie geparst.
