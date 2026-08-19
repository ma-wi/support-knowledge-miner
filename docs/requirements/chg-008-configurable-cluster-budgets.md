# Konfigurierbare LLM-Taxonomie-Budgets

- Requirement ID: chg-008-configurable-cluster-budgets
- Status: implemented
- Decision owner: mawi
- Last updated: 2026-08-15

## Problem

Die festen Grenzwerte für `llm_taxonomy` können bei größeren, aber bewusst
freigegebenen Projekten die Konsolidierung verhindern. Die generische Budgetmeldung
nennt keine Möglichkeit, die projektspezifische Kapazität kontrolliert anzupassen.

## Desired outcome

Der bestehende Projekt-Tab `Einstellungen` verwaltet die drei für
`llm_taxonomy` relevanten Soft-Limits. Neue Cluster-Set-Jobs übernehmen einen
unveränderlichen Snapshot der zum Startzeitpunkt gültigen Projektwerte. Serverseitige
Hard-Caps verhindern unbegrenzten Prompt- und Speicherverbrauch.

## Scope

- maximale aktive, nicht fixierte Taxonomie-Quellcluster: Standard 200, Bereich 1–500;
- maximale Taxonomie-Promptzeichen: Standard 80.000, Bereich 10.000–500.000;
- maximales gesamtes Keyword-Vokabular: Standard 250.000, Bereich 1.000–1.000.000;
- persistente Projektwerte, API-Felder, Settings-Formular und Job-Snapshot;
- bestehender Fehlercode `VALIDATION_FAILED` für ungültige Einstellungen;
- bestehender Fehlercode `CLUSTER_BUDGET_EXCEEDED` für überschrittene Joblimits.

## Non-goals

- Konfiguration des allgemeinen 5-GiB-Vektor-Arbeitsspeicherbudgets;
- unbegrenzte oder installationsweite Ressourcenfreigaben;
- Änderung der LLM-Provider-Kontextfenster.

## Acceptance criteria

- AC-1: Bestehende Projekte erhalten ohne Eingriff die bisherigen drei Standardwerte.
- AC-2: Ein berechtigter Nutzer kann alle drei Werte im Projekt-Tab `Einstellungen`
  innerhalb der dokumentierten Hard-Caps speichern und nach einem Reload wiedersehen.
- AC-3: Ungültige Werte liefern `VALIDATION_FAILED` mit feldbezogenen sicheren
  Meldungen; Eingaben bleiben erhalten und es erscheint kein Erfolgsfeedback.
- AC-4: Ein neuer `llm_taxonomy`-Job speichert die Projektwerte im Source-Snapshot
  und verwendet exakt diesen Snapshot für Quellcluster-, Prompt- und
  Keyword-Vokabularprüfung.
- AC-5: Bereits angelegte Cluster-Sets ohne Budget-Snapshot verwenden weiterhin die
  bisherigen Defaults.
- AC-6: Projektisolation, feste Hard-Caps, Auditierung und bestehende
  `CLUSTER_BUDGET_EXCEEDED`-Semantik bleiben erhalten.
- AC-7: API-, Service-, Migrations-, Job- und Frontendtests decken Erfolg,
  Grenzwerte, Invalidität, Snapshotstabilität und sichere Fehlerdarstellung ab.
