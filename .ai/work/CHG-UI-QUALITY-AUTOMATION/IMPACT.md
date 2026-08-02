# Change impact: Automatisierte UI-Qualitätsgates

- Change ID: CHG-UI-QUALITY-AUTOMATION
- Status: accepted
- Change request: `.ai/work/CHG-UI-QUALITY-AUTOMATION/CHANGE.md`
- Last updated: 2026-07-30

## Search scope and current-state findings

Untersucht wurden `.ai/project.yaml`, generierte Gate-Defaults,
`ui-quality.sh`, `check-ui-quality.py`, `orchestrate.py`, Frontendmanifest und
Lockfile, Vite-Konfiguration, bestehende Vitest-Tests, Designrichtlinien und
Contributor-Dokumentation. Es existiert kein Browser- oder Accessibility-Runner.

## Impact matrix

| Layer or concern | Located artifact / current owner | Action | Required end state | Owning task | Verification evidence |
|---|---|---|---|---|---|
| UI and interaction state | `frontend/src/` | keep | Kein Produktverhalten ändert sich | T001 | bestehende Frontendtests |
| Frontend validation and feature model | `frontend/src/App.tsx` | keep | Keine Modelländerung | T001 | Typecheck und Tests |
| API client / generated artifacts | Fetch-Aufrufe in `App.tsx` | keep | Runner blockiert externe Requests und simuliert nur bekannte lokale Antworten | T001 | Runner-Negativtests |
| Public API or message contract | FastAPI `/api/*` | not-applicable | Kein Vertragsänderung | T001 | Repository-Diff |
| Backend schema and application service | `backend/` | not-applicable | Kein Backendzugriff für Browsergates | T001 | Runner-Konfiguration |
| Domain model and business rules | `backend/*/service.py` | not-applicable | Unverändert | T001 | Repository-Diff |
| Persistence and migration | PostgreSQL/Migrationen | not-applicable | Keine Datenbank erforderlich | T001 | Browserlauf ohne Backend |
| Integrations, jobs, events, caches, search | Vite-Testserver | modify | Nur Loopback, fester Port, gebundener Prozesslebenszyklus | T001 | fokussierte Tests |
| Telemetry and operations | UI-Evidence unter `.ai/work/` | modify | Revisionsgebundenes Manifest und begrenzte Berichte | T001 | `check-ui-quality.py` |
| Tests and fixtures | Vitest ohne Browserautomation | modify | Runner-Unit-/Integrationstests und geprüfte Baselines | T001 | npm-Skripte |
| Documentation and specifications | README und PROJECT_CONTEXT | modify | Aktuelle Setup-/Gate-Kommandos; keine Produktspezifikation erforderlich | T001 | `check-docs.py` |
| Dependency/build chain | `frontend/package.json`, Lockfile | modify | Playwright Chromium und Axe exakt versioniert, locked und gescannt | T001 | Dependency-/Security-Gates |
| UI-quality configuration | `.ai/project.yaml`, Defaults | modify | Drei ausführbare Gate-Kommandos aktiviert | T001 | Bootstrap und State-Check |

## New or parallel artifacts

| Proposed artifact | Existing responsibility searched | Why extension/replacement is insufficient | Compatibility need | Removal criterion |
|---|---|---|---|---|
| `.ai/tools/ui-browser-review.mjs` | Dispatcher und statischer Validator | Browserprozess, Netzwerkisolation, Screenshots, Axe und Pixelvergleich benötigen projektspezifische Ausführung | Bestehende Dispatcher-Schnittstelle bleibt | Zusammen mit konfigurierten Commands und Dependencies entfernen |
| `frontend/ui-baselines/` | Keine Baselines vorhanden | Visuelle Regression braucht überprüfte Referenzbilder | Nur Chromium/Linux-basierter Gate | Bei Ersatz des Visual-Regression-Verfahrens entfernen |

## Conditional impact annexes

## UI classification

- Design class: 0
- Rationale, including verified no-UI-impact reason for class 0: Nur Entwicklungs-
  und Reviewtooling; `frontend/src` bleibt unverändert.
- Highest design class assigned: 0
- Implementation-start design class: 0
- Prototype strategy: none
- Prototype artifact/revision: not-applicable
- Required tool dependencies and owning package: `@playwright/browser-chromium`,
  `playwright-core` und `@axe-core/playwright` im Frontend-Development-Paket
- Existing pattern/components reused: not-applicable
- Applicable design-system rule: not-applicable
- Design approval status: not-required
- Visual review required: no
- Required screens: not-applicable
- Required states: not-applicable
- Required viewports: not-applicable

## Superseded artifacts

| Artifact | Disposition: remove/deprecate/replace/retain | Reason if retained | Owning task | Removal criterion or evidence |
|---|---|---|---|---|
| none | retain | Kein bestehender Browser-Runner vorhanden | T001 | Suchnachweis |

## Concept-trace completion

- Repository-wide search terms and symbols: `browser_review`,
  `BROWSER_REVIEW_CMD`, `visual_regression`, `accessibility`, `playwright`,
  `screenshot`, `manifest.json`
- Generated sources traced to their authoritative input: yes
- No relevant references remain unclassified: yes
- Uncertainty or intentionally excluded areas: Authentifizierte Produktzustände
  werden erst bei konkreten UI-Changes als zusätzliche Szenarien ergänzt.

## Acceptance

- Impact analysis complete: yes
- Accepted by: mawi
- Date: 2026-07-30
