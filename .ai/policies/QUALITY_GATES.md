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
| Documentation check | Mandatory | Review | Changed behavior must be documented |
| Independent review | Mandatory for normal/significant work | PR or review report | Fresh context required |

## Gate execution policy

During implementation, run the smallest relevant checks. Before completion, run all configured mandatory gates through `./.ai/tools/verify.sh`, including locked setup for configured projects.

A non-mandatory gate may be skipped only when:

- it is explicitly not applicable; or
- the environment cannot execute it and the limitation is reported.

A skipped mandatory gate fails immediately. Gate commands and required flags are
committed in `.ai/config/project.defaults.env`. Ignored `.ai/config/project.env`
may customize focused gate commands but cannot weaken committed requiredness and is
ignored by full `verify.sh`.

## Failure policy

When a gate fails:

1. preserve the failure evidence;
2. identify the root cause;
3. fix the implementation or test, not the gate;
4. re-run the focused gate;
5. re-run the full verification suite.

Do not disable rules, delete tests, reduce coverage, suppress findings, or change thresholds merely to obtain a passing result.

## Required project decisions

- Minimum coverage policy: Neue Funktionen und Bugfixes brauchen passende automatische Tests. Es gibt vorerst keine feste Prozentzahl.
- Supported runtime matrix: Unterstützt wird nur die Umgebung, die in GitHub Actions läuft und durch die Dateien im Repository festgelegt ist.
- Warning-as-error policy: Warnungen aus Linting, Typprüfung, Build oder Security-Checks sollen wie Fehler behandelt und behoben werden.
- Security severity threshold: Kritische und hohe Sicherheitsprobleme blockieren den Merge.
- Dependency update policy: Neue oder aktualisierte Abhängigkeiten müssen begründet und mit Lockfile eingecheckt werden.
- Flaky-test policy: Unzuverlässige Tests werden repariert; sie dürfen nicht einfach ignoriert oder gelöscht werden.
- CI required checks: Vor dem Merge muss GitHub Actions mit `./.ai/tools/verify.sh` erfolgreich durchlaufen.

## Dependency and package gate

Run `./.ai/tools/check-dependencies.sh` for changes to manifests, lockfiles, build
logic, registries, or generated dependency metadata. It enforces source and lockfile
policy and invokes configured vulnerability, license, or reputation scanners. Manual
provenance and license review remains required where automation cannot decide.
