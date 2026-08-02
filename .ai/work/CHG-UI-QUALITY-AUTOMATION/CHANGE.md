# Incremental change: Automatisierte UI-Qualitätsgates

- Change ID: CHG-UI-QUALITY-AUTOMATION
- Status: ready-for-implementation
- Requirement: `docs/requirements/chg-ui-quality-automation.md`
- Work directory: `.ai/work/CHG-UI-QUALITY-AUTOMATION/`
- Decision owner: mawi
- Last updated: 2026-07-30

## Trigger and problem

UI-Qualität und Orchestrierung sind aktiviert, aber Browser Review, Visual Regression
und Accessibility besitzen keine ausführbaren Kommandos.

## Current behavior

`.ai/tools/ui-quality.sh` orchestriert konfigurierte Kommandos und
`check-ui-quality.py` validiert Evidence. Projektgebundene Browserautomation,
Baselines und Accessibility-Prüfung fehlen.

## Desired end state

Die bestehende UI-Quality-Orchestrierung ruft drei locked, fail-closed arbeitende
Host-Kommandos auf. Ein geschützter Runner erzeugt nur lokale synthetische Evidenz,
prüft Accessibility und vergleicht genehmigte Screenshots.

## Invariants

- Keine Produktionszugriffe oder echten Daten.
- Keine Änderung am sichtbaren Produktverhalten.
- Evidence bleibt auf das aktive `.ai/work/<id>/evidence/ui/` begrenzt.
- Baselines werden nie während eines normalen Gates automatisch aktualisiert.
- Unbekannte oder externe Browserrequests werden blockiert.

## Scope

### In scope

- Frontend-Development-Dependencies und Lockfile.
- Geschützter UI-Browser-Runner, Tests, Baselines und npm-Skripte.
- `.ai/project.yaml`, generierte Gate-Konfiguration und Contributor-Dokumentation.

### Out of scope / non-goals

- Neue Produktkomponenten oder Screens.
- Authentifizierte Produkt-End-to-End-Abdeckung.
- Externe Browser-/Screenshot-Dienste.

## Canonical capability specifications affected

- not-required: Die Änderung betrifft ausschließlich Entwicklungs- und Reviewtooling.

## Existing responsibility decision

- Current owner of the behavior: `.ai/tools/ui-quality.sh` und `check-ui-quality.py`
- Decision: extend
- Why a new artifact is or is not required: Der bestehende Gate-Dispatcher bleibt
  erhalten; ein projektgebundener Browser-Runner ist für echte Browserausführung,
  Evidence und Bildvergleich erforderlich.
- Parallel compatibility behavior, if any: Der manuelle Fallback bleibt dokumentiert,
  wird bei aktivierter Orchestrierung aber nicht verwendet.
- Removal criterion for retained legacy behavior: not-applicable; kein paralleler
  automatisierter Runner existiert.

## Compatibility, migration, and recovery

- Existing clients or callers: `verify.sh`, `ui-quality.sh` und `orchestrate.py`
- Data migration: not-applicable
- Deployment ordering: Dependencies und Runner müssen vor Aktivierung der drei
  Kommandos eingecheckt sein.
- Rollback or recovery: Kommandos deaktivieren, Dependencies/Runner/Baselines
  gemeinsam zurücknehmen und Defaults erneut generieren.
- Deprecation window, if any: none

## Conditional change annexes

## Design classification

- Class: 0
- Highest design class assigned: 0
- Implementation-start design class: 0
- Rationale: Entwicklungs- und Reviewtooling ändert weder gerenderte UI noch
  Interaktionen des Produkts.
- Existing pattern/components reused: not-applicable; kein Produkt-UI-Code betroffen
- Applicable design-system rule: not-applicable; keine sichtbare Änderung
- Existing screens affected: none
- Prototype strategy: none
- Visual review required: no
- Required screens: not-applicable
- Required states: not-applicable
- Required viewports: not-applicable
- DESIGN_DELTA.md required: no
- Design decision owner, when required: not-applicable

### Classification history

| Date | Previous class | New class | Reason | Approved by |
|---|---:|---:|---|---|
| 2026-07-30 | 0 | 0 | Tooling ohne sichtbare Produktänderung | mawi |

## Component impact

### Existing components reused

not-applicable: Kein Produkt-UI-Code betroffen.

### Existing components extended

not-applicable: Kein Produkt-UI-Code betroffen.

### New shared components

not-applicable: Keine Produktkomponenten.

### New feature-local components

not-applicable: Keine Produktkomponenten.

### Components replaced or removed

none

### Rejected reuse options

Unit- und jsdom-Tests ersetzen keine Browser-, Accessibility- oder visuelle Evidenz.

### Rationale

Designklasse 0; der Runner prüft bestehende UI, verändert sie aber nicht.

## Acceptance criteria

- [ ] AC-1 bis AC-6 aus
  `docs/requirements/chg-ui-quality-automation.md`.

## Open questions and blockers

- Keine. Der Browser wird ausschließlich für lokale synthetische Zustände installiert.

## Readiness decision

- Shared understanding confirmed: yes
- Confirmed by: mawi durch Implementierungsauftrag
- Confirmation date: 2026-07-30
- Impact analysis accepted: yes
- Ready for implementation: yes
- Remaining blockers: none
