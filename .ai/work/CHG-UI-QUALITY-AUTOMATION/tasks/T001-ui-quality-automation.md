# Task T001: UI-Qualitätsautomation integrieren

- Status: blocked
- Parent requirement or change: `docs/requirements/chg-ui-quality-automation.md`
- Plan: `.ai/work/CHG-UI-QUALITY-AUTOMATION/PLAN.md`
- Work type: incremental-change
- Review batch: RB001
- Depends on: none
- Owner/agent: implementer
- Last updated: 2026-07-30

## Objective

Alle Impact-Zeilen erreichen durch einen locked, lokal isolierten Browser-Runner,
konfigurierte Commands, Baselines, Tests und Dokumentation den gewünschten Endzustand.

## Scope

### In scope

Runner, Dependencies, Lockfile, Konfiguration, Baselines, Tests und Dokumentation.

### Out of scope

Produkt-UI, Backend, Datenbank und externe Dienste.

## Preconditions

Owner-Auftrag und akzeptierte Change-/Impact-Artefakte liegen vor.

## Impact and responsibility

- `IMPACT.md` rows closed: alle
- Existing responsibility extended/replaced/deprecated/removed: UI-Quality-Dispatcher
  und Projektkonfiguration werden erweitert.
- New or parallel artifacts and accepted justification: Ein geschützter Browser-Runner
  und Referenzbilder sind mangels bestehender Ausführungsschicht erforderlich.
- Superseded artifacts assigned to this task: none

## Affected files or components

`.ai/tools/ui-browser-review.mjs`, `.ai/tools/ui-vite.config.mjs`,
`.ai/project.yaml`, `.ai/config/project.defaults.env`,
`frontend/package*.json`, `frontend/ui-baselines/`, README und PROJECT_CONTEXT.

## Acceptance criteria

- [ ] AC-1 bis AC-6 des Parent Requirements.

## Security Assurance

- Security assurance: required
- Security triggers: dependency/build chain, Trusted-Host-Command, Dateischreiben,
  lokaler HTTP-Server und untrusted Browserinhalt
- Assets and data classes: Repositoryinhalt und synthetische interne Testdaten;
  keine Secrets oder personenbezogenen Daten
- Trust boundaries and untrusted inputs: Browserresponses, CURRENT_PLAN-Pfad,
  Konfiguration, Baselinebilder, lokaler HTTP-Port und Dependencycode
- Authorization model: Nur der vertrauenswürdige Host startet den Runner; Pfade
  müssen unter dem aktiven Work-Evidence-Verzeichnis liegen.
- Threats and abuse cases: Pfadtraversal/Symlinks, externe Browserrequests,
  Port-Hijacking, hängenbleibende Prozesse, automatische Baseline-Manipulation,
  übergroße Dateien und Supply-Chain-Kompromittierung
- Mitigations: Strikte Pfad-/Symlinkprüfung, Loopback-Allowlist, Request-Abbruch,
  WebSocket-Sperre, redigierte URL-Diagnosen, direkter Aufruf ausschließlich
  geschützter Runner-/Vite-Konfiguration statt änderbarer npm-Hooks, fester
  exklusiver Port, Timeouts/Prozessgruppen-Cleanup, getrenntes explizites
  Baseline-Update, Größenlimits, exakte Versionen, Lockfile und Scanner
- Security verification: Negativtests für Pfade/URL/Requests/Bildvergleich,
  Dependency-Audit, Bandit und adversariales Diff-Review
- Residual security risk: Browser- und Accessibility-Dependencies führen
  Drittcode lokal aus; auf locked Development-/CI-Umgebung begrenzt.
- Specialist security review: erforderlich vor Abschluss

## Conditional task annexes

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

Unit-Tests und manuelle Screenshots erfüllen den automatisierten Host-Gate-Vertrag
nicht.

### Rationale

Toolingintegration ohne sichtbare Produktänderung.

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

## Implementation constraints

Keine Shellausführung aus untrusted Eingaben; keine externen URLs; keine
automatischen Baselineupdates im Gate; ausschließlich synthetische Daten.

## Applicable capability specification and test seam

- Specification criteria: AC-1 bis AC-6 des Requirements
- Primary observable boundary for this task: npm-Gatecommands und erzeugte
  Evidence-/Reportdateien
- Implementation-specific boundaries to avoid testing directly: interne
  Playwright-Protokolldetails

## Verification

- [x] Focused tests
- [x] Relevant linting and static analysis
- [x] Security or dependency checks when applicable
- [x] Documentation assessment, including `README.md` and `.ai/PROJECT_CONTEXT.md`

Exact commands:

```bash
npm --prefix frontend run test:ui-quality-runner
npm --prefix frontend run visual:evidence
npm --prefix frontend run accessibility
npm --prefix frontend run visual:regression
./.ai/tools/check-ui-quality.py
./.ai/tools/check-dependencies.sh
./.ai/tools/verify.sh
```

## Risks or blockers

Initiale Baselines müssen mit dem locked Chromium auf dieser Linux-Umgebung erzeugt
und visuell geprüft werden.

Der bestehende Login-Button verwendet Weiß auf `#0891b2` (3,68:1). Axe meldet
deshalb in allen vier geprüften Zuständen `color-contrast` als schwerwiegenden
Verstoß. Das Accessibility-Gate arbeitet damit korrekt, kann aber ohne eine
sichtbare und separat freizugebende Produktänderung noch nicht grün werden.

## Result

Browser Review und Visual Regression bestehen mit vier Desktop-/Mobile-Zuständen.
Der Accessibility-Runner und sein Negativtest arbeiten korrekt; der reale Lauf
bleibt wegen des dokumentierten bestehenden Kontrastverstoßes blockiert.

### Adversarial pre-review

- Adversarial pre-review: completed
- Pre-review lenses: Security, Dependencies, UI quality, Compatibility, Documentation
- Pre-review evidence: Der ursprüngliche Trusted-Host-Command lief indirekt über
  änderbare npm-Skripte. Die Trust Chain wurde auf direkte geschützte
  Runner-/Vite-Aufrufe umgestellt; blockierte URLs werden redigiert und reale
  Symlink-Ablehnung ist getestet.
- Open P0/P1 findings: P1 contract completion blocker: AC-3 remains blocked by
  the existing product contrast defect; no open implementation P0/P1.
