# Implementation plan: Automatisierte UI-Qualitätsgates

- Status: blocked
- Change class: normal
- Work type: incremental-change
- Requirement: `docs/requirements/chg-ui-quality-automation.md`
- Change request: `.ai/work/CHG-UI-QUALITY-AUTOMATION/CHANGE.md`
- Change impact: `.ai/work/CHG-UI-QUALITY-AUTOMATION/IMPACT.md`
- Canonical capability specifications: not-required
- Work directory: `.ai/work/CHG-UI-QUALITY-AUTOMATION/`
- Last updated: 2026-07-30

## Outcome and implementation boundary

- In scope: Lokaler Chromium-Runner, Evidence, Axe, visuelle Baselines, Commands,
  locked Dependencies, Tests und Contributor-Dokumentation.
- Non-goals: Produkt-UI-, API- oder Datenbankänderungen; externe Browserdienste.
- Accepted assumptions relevant to implementation: Die stabile abgemeldete
  Anwendung und ein synthetischer Fehlerzustand bilden den initialen Baselineumfang.
- Open blockers: Der echte Accessibility-Lauf erkennt im bestehenden Login-Button
  einen zu niedrigen Textkontrast (3,68:1 statt 4,5:1). Eine sichtbare
  Produktänderung ist nicht Teil der akzeptierten Designklasse 0.

## Current-state findings and approach

- Relevant existing responsibilities, components, contracts, and test seams:
  `ui-quality.sh` dispatcht Commands; `check-ui-quality.py` validiert Manifest und
  Screens; Vite stellt die reale Frontend-Anwendung bereit.
- Desired end state implemented by this plan: Drei Commands nutzen einen
  geschützten gemeinsamen Runner und scheitern bei fehlender Isolation/Evidenz.
- Existing responsibility to extend/replace/deprecate/remove: Bestehenden
  UI-Quality-Dispatcher erweitern, nicht ersetzen.
- Proposed implementation: Node-ESM-Runner unter `.ai/tools/`, Chromium aus dem
  Frontend-Paket, geschützte Vite-Konfiguration ohne änderbaren npm-Hook,
  synthetische Same-Origin-API-Antworten, Axe-Bericht und browserinterner
  PNG-Pixelvergleich.
- New or parallel artifacts and accepted justification: Runner und Baselines sind
  neue, bisher nicht vorhandene Verantwortungen.
- Alternatives rejected for implementation reasons: `true`/Unit-Tests erzeugen
  keine Evidence; externe Screenshotdienste verletzen lokale Isolation; ein
  automatisch aktualisierender Baseline-Gate wäre nicht reviewbar.

## Affected areas

- Components and interfaces: `.ai/tools/ui-browser-review.mjs`,
  `.ai/tools/ui-vite.config.mjs`, npm-Komfortskripte und der geschützte
  UI-Quality-Commandvertrag.
- Data and migrations: Keine Produktdaten; temporäre synthetische Evidence.
- Dependencies and configuration: `@playwright/browser-chromium@1.62.0` und
  `playwright-core@1.62.0` (Apache-2.0, Microsoft Playwright; Browserartefakt und
  Automations-API) sowie `@axe-core/playwright@4.12.1` (MPL-2.0, Deque,
  WCAG-Analyse). Standardbibliothek
  und bestehende Dependencies besitzen keinen Browser-/Accessibility-Engine-Ersatz.
  Beide sind dev-only, lockfile-gebunden und gemeinsam mit dem Runner entfernbar.
- Deployment and operations: Nur lokale/CI-Entwicklungsumgebung, Loopback-Port 5173.
- Documentation: README und PROJECT_CONTEXT.

## Conditional plan annexes

## UI classification

- Design class: 0
- Prototype strategy: none
- Visual review required: no

## Component impact

### Existing components reused

not-applicable: Kein Produkt-UI-Code betroffen.

### Existing components extended

not-applicable: Kein Produkt-UI-Code betroffen.

### New shared components

| Name/responsibility | Target path/layer | API/variants/states | Tests | Accessibility | Story/equivalent | Catalog entry |
|---|---|---|---|---|---|---|
| none | not-applicable | not-applicable | not-applicable | not-applicable | not-applicable | not-applicable |

### New feature-local components

none

### Components replaced or removed

none

### Rejected reuse options

Bestehende jsdom-Tests besitzen keine echte Browser-, Axe- oder Pixelvergleichsgrenze.

### Rationale

Designklasse 0; ausschließlich Qualitätsinfrastruktur.

## Prototype relationship

- Prototype artifact: not-applicable
- Elements to promote: none
- Prototype-only elements to discard: none
- Tool dependencies and owning package: Frontend-Development-Paket

## Visual evidence

- Required screens: not-applicable
- Required states: not-applicable
- Required viewports: not-applicable
- Manifest: not-required for design class 0

## Risks and recovery

- Compatibility/migration: Chromium-Baselines sind plattformgebunden; Gate läuft
  bewusst mit dem locked Browser auf Linux.
- Performance/reliability: Browserprozesse und Vite-Server erhalten Timeouts,
  festen Port und garantierte Beendigung.
- Rollback/recovery: Commands deaktivieren, Defaults regenerieren und Runner,
  Baselines sowie Dependencies gemeinsam entfernen.

## Security Assurance routing

- Security assurance: required
- Security triggers: dependency/build chain, commands, files, local network
- Threat model: not-required: Die vollständige Bedrohungsanalyse ist im einzigen
  Work Item enthalten.
- Specialist security review: required: Dependency-, Pfad-, Prozess- und
  Netzwerkisolation im unabhängigen Review

## Review cadence

- Cadence: per-task
- Maximum tasks per review batch: 1
- Forced per-task review triggers present: dependency-change
- Rationale: Neue ausführbare Supply-Chain-Inputs und Trusted-Host-Command.

## Work items

| ID | Vertical outcome | Status | Depends on | Review batch | Impact rows closed | Task file |
|---|---|---|---|---|---|---|
| T001 | Drei vollständig integrierte UI-Qualitätsgates | blocked | none | RB001 | alle | `tasks/T001-ui-quality-automation.md` |

## Acceptance-criteria traceability

| Criterion in durable requirement/specification | Work item | Automated verification |
|---|---|---|
| AC-1, AC-2 | T001 | Browsercommand, Manifestvalidator |
| AC-3 | T001 | Axe-Runner und Negativtest |
| AC-4 | T001 | Pixelvergleich und Negativtest |
| AC-5 | T001 | Runner-Unit-/Integrationstests |
| AC-6 | T001 | Dependency-, Security- und Full-Verify-Gates |

## Superseded-artifact and canonical-spec closeout

- Superseded artifacts assigned for removal/deprecation: none
- Repository-wide orphan searches required: Browsercommand- und Dependency-Namen
- Capability specifications to update in place: none
- Temporary compatibility behavior and removal criteria: none

## Verification and closeout

- Focused commands: npm-Runner-Tests, drei UI-Commands,
  `check-ui-quality.py`, `check-dependencies.sh`
- Full command: `./.ai/tools/verify.sh`
- Specialist review required and why: Security-fokussiertes unabhängiges Review
  wegen Trusted-Host-Ausführung und Dependencies.
- Durable documentation/ADR updates, including `README.md` and
  `.ai/PROJECT_CONTEXT.md` assessment: Beide erhalten Setup-/Commandhinweise; kein
  ADR erforderlich, da vorhandene UI-Quality-Architektur nur konkretisiert wird.
- Temporary artifacts to remove after review: gesamtes aktives Work-Verzeichnis und
  Evidence; Requirement bleibt als akzeptierter Ursprung erhalten.

## Material deviations

- Der neu aktivierte Accessibility-Gate hat einen bereits vorhandenen
  WCAG-Kontrastverstoß sichtbar gemacht. Der Runner unterdrückt ihn nicht; die
  Behebung benötigt eine separat akzeptierte sichtbare UI-Änderung.
