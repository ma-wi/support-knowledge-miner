# Requirement: Automatisierte UI-Qualitätsgates

- Requirement ID: CHG-UI-QUALITY-AUTOMATION
- Work type: incremental-change
- Affected capability specifications: not-required; the product contract is unchanged

## Problem

Die aktivierte UI-Qualitätskonfiguration besitzt keine ausführbaren Kommandos für
Browser Review, Accessibility und Visual Regression. Dadurch kann der
Repository-Orchestrator keinen vertrauenswürdigen Host-Browser-Gate ausführen.

## Desired outcome

Das Repository stellt reproduzierbare, lokal begrenzte Browserautomation bereit.
Sie erzeugt revisionsgebundene Browser-Evidenz, prüft WCAG-Verstöße automatisiert
und vergleicht stabile Screenshots mit geprüften Baselines.

## Functional requirements

- FR-1: Browser Review startet ausschließlich die lokale Vite-Testanwendung auf der
  konfigurierten Loopback-URL.
- FR-2: Der Runner blockiert ausgehende Browserzugriffe und verwendet ausschließlich
  synthetische Testdaten.
- FR-3: Browser Review schreibt Screenshots und ein gültiges Manifest ausschließlich
  unter `.ai/work/<change-id>/evidence/ui/`.
- FR-4: Accessibility prüft die stabilen Browserzustände automatisiert und schreibt
  einen maschinenlesbaren Bericht in das aktive Evidence-Verzeichnis.
- FR-5: Visual Regression vergleicht Desktop- und Mobile-Screenshots mit
  eingecheckten, explizit aktualisierbaren Baselines und schlägt bei relevanter
  Abweichung fehl.
- FR-6: Fehlende aktive Arbeit, ungültige Pfade, belegte Ports, fehlende Browser,
  Netzwerkzugriffe, Accessibility-Verstöße und visuelle Abweichungen führen
  fail-closed zu einem Exitcode ungleich null.

## Non-functional requirements

- Security: Keine Produktionsressourcen, Secrets, echten Konten oder externen
  Netzwerkziele werden verwendet.
- Reproducibility: Toolversionen und Browserartefakte sind über
  `frontend/package-lock.json` gebunden.
- Operability: Die drei Gates sind über committed npm-Skripte und
  `.ai/project.yaml` ausführbar.
- Compatibility: Produktcode, öffentliche APIs und bestehende Unit-/Integrationstests
  bleiben unverändert.

## In scope

- Chromium-basierter Browser-Runner.
- Revisionsgebundenes Evidence-Manifest.
- Axe-basierte Accessibility-Prüfung.
- Pixelbasierte Visual Regression mit explizitem Baseline-Update.
- Dependency-, Konfigurations- und Contributor-Dokumentation.

## Out of scope / non-goals

- Änderung des sichtbaren Produktdesigns.
- Vollständige End-to-End-Abdeckung aller authentifizierten Produktabläufe.
- Zugriff auf Produktion oder echte Supportdaten.
- Automatische Freigabe visueller Änderungen.

## Acceptance criteria

- [ ] AC-1: Alle drei konfigurierten UI-Kommandos sind installiert, locked und lokal
  ausführbar.
- [ ] AC-2: Browser Review erzeugt gültige Desktop-/Mobile-Evidenz und ein Manifest,
  das `check-ui-quality.py` akzeptiert.
- [ ] AC-3: Accessibility schlägt bei einem injizierten schwerwiegenden Verstoß fehl
  und besteht für die geprüften aktuellen Zustände.
- [ ] AC-4: Visual Regression schlägt bei einer veränderten Aufnahme fehl und
  besteht gegen die akzeptierten Baselines.
- [ ] AC-5: Pfad- und Netzwerkgrenzen sind negativ getestet.
- [ ] AC-6: Dependency-, Security-, Test-, Build- und vollständige Projektgates
  bestehen ohne offene P0/P1-Findings.

## Approval

- Owner: mawi
- Status: accepted
- Date: 2026-07-30
