# Quality gates

Bootstrap derives executable stack gates into committed
`.ai/config/project.defaults.env`. Complete the project decisions below before full
verification can pass.

| Gate | Policy | Canonical command | Notes |
|---|---|---|---|
| Locked setup | Required when dependencies or generated tool defaults require installation | `./.ai/tools/ci-setup.sh` through `./.ai/tools/verify.sh` | Uses committed setup command |
| Formatting | Required when the enabled stack has a formatter | `./.ai/tools/format.sh --check` | No formatting drift |
| Linting | Required for every enabled code stack | `./.ai/tools/lint.sh` | Include static analysis where applicable |
| Static typing | Conditional | Included in lint/build | Required for typed projects |
| Unit tests | Mandatory | `./.ai/tools/test.sh` | Behavior changes require tests |
| Integration tests | Conditional | Included in test command | Required for component interactions |
| End-to-end tests | Conditional | Project-specific | Required for critical user flows |
| Build/package | Required when the project produces an artifact | `./.ai/tools/build.sh` | Must produce expected artifact |
| Secret scan | Required before the repository handles credentials or secret-bearing configuration | CI or configured `SECURITY_CMD` | Source-host scanning may satisfy this decision |
| Dependency policy/scan | Mandatory when manifests exist | `./.ai/tools/check-dependencies.sh` | Lockfile-aware policy and vulnerability audit |
| Static security analysis | Conditional | `./.ai/tools/security.sh` | Mandatory for security-sensitive code |
| License policy | Conditional | Project-specific | Required when distribution demands it |
| Migration validation | Conditional | Project-specific | Include upgrade and rollback behavior |
| Documentation check | Mandatory | `./.ai/tools/check-docs.py` through `verify.sh` | Changed behavior and canonical references must be consistent |
| Work-state consistency | Mandatory when `.ai/work/` or `CURRENT_PLAN.md` is active | `./.ai/tools/check-work-state.py` through `verify.sh` | Phase/status/artifact cross-check |
| Incremental-change impact | Conditional for active incremental changes | `./.ai/tools/check-change-impact.py` through `verify.sh` | CHANGE/IMPACT/plan/task consistency |
| Independent review | Mandatory for normal/significant work | PR or review report | Fresh context required |
| UI structure and isolation | Conditional when UI quality is enabled and active work has UI impact | `./.ai/tools/check-ui-quality.py` | Phase-aware static checks |
| Browser and screenshot evidence | Conditional for UI design class 1–3 | Configured command or documented manual gate | Identifies revision, state, and viewport |
| Independent visual review | Conditional for UI design class 1–3 | Visual-review report | Does not replace code review |
| Accessibility and visual regression | Project-configured | `.ai/tools/ui-quality.sh` | Empty command is not a pass |
| User-facing error contract | Conditional when error handling is enabled and active work changes an affected action | `./.ai/tools/check-user-facing-errors.py` | Phase-aware catalog, matrix, mapping, recovery, negative-test, and source-pattern checks |
| Orchestration state | Mandatory when orchestration is enabled or runtime state exists | `./.ai/tools/check-orchestration-state.py` through `verify.sh` | Read-only schema, queue, checkpoint, lease/event, Git-digest, and lifecycle consistency |

## Gate execution policy

During implementation, run the smallest relevant checks. Before completion, run all configured mandatory gates through `./.ai/tools/verify.sh`, including locked setup for configured projects.

A non-mandatory gate may be skipped only when:

- it is explicitly not applicable; or
- the environment cannot execute it and the limitation is reported.

A skipped mandatory gate fails immediately. Gate commands and required flags are
committed in `.ai/config/project.defaults.env`. Ignored `.ai/config/project.env`
may customize focused gate commands but cannot weaken committed requiredness and is
ignored by full `verify.sh`; the latter sets
`AGENT_TEMPLATE_IGNORE_LOCAL_OVERRIDES=1` internally. Do not set that variable
manually.

UI-tool dependencies selected by a project or change must be installed through the
configured package manager, committed with the applicable lockfile, and checked by
the dependency and build gates. Prototype-only dependencies remain in the private
prototype package and are removed with it.

Error-handling static checks do not prove message comprehension, complete runtime
coverage, accessibility, or correct recovery. Required backend, contract, frontend,
browser, visual, and independent-review evidence remains mandatory and a skipped
required browser/visual check is not a pass.

## Failure policy

When a gate fails:

1. preserve the failure evidence;
2. identify the root cause;
3. fix the implementation or test, not the gate;
4. re-run the focused gate;
5. re-run the full verification suite.

Do not disable rules, delete tests, reduce coverage, suppress findings, or change thresholds merely to obtain a passing result.

## Required project decisions

- Project decisions reviewed: yes
- Minimum coverage policy: Neue Funktionen und Bugfixes brauchen passende automatische Tests. Es gibt vorerst keine feste Prozentzahl.
- Supported runtime matrix: Unterstützt wird nur die Umgebung, die in GitHub Actions läuft und durch die Dateien im Repository festgelegt ist.
- Warning-as-error policy: Warnungen aus Linting, Typprüfung, Build oder Security-Checks sollen wie Fehler behandelt und behoben werden.
- Security severity threshold: Kritische und hohe Sicherheitsprobleme blockieren den Merge.
- Dependency update policy: Neue oder aktualisierte Abhängigkeiten müssen begründet und mit Lockfile eingecheckt werden.
- Flaky-test policy: Unzuverlässige Tests werden repariert; sie dürfen nicht einfach ignoriert oder gelöscht werden.
- CI required checks: Vor dem Merge muss GitHub Actions mit `./.ai/tools/verify.sh` erfolgreich durchlaufen.

Review and adapt every decision for the concrete project, then set
`Project decisions reviewed: yes`. The seeded examples are not an implicit project
decision, and configured-project verification fails while this field is not `yes`.

## Dependency and package gate

Run `./.ai/tools/check-dependencies.sh` for changes to manifests, lockfiles, build
logic, registries, or generated dependency metadata. It enforces source and lockfile
policy and invokes configured vulnerability, license, or reputation scanners. Manual
provenance and license review remains required where automation cannot decide.
