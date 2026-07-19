# Dependency and package policy

Third-party packages are untrusted executable supply-chain inputs. Adding or upgrading a dependency is a security-relevant change.

## Required review for new direct dependencies

Record in the durable specification, implementation plan, or pull request as appropriate:

- package name, ecosystem, version or version range, and purpose;
- why the standard library or an existing dependency is insufficient;
- maintenance status and release activity;
- publisher/maintainer identity and notable ownership changes;
- known vulnerabilities and available fixed versions;
- license and compatibility with the project;
- install/build scripts, native code, generated code, and network access;
- number and risk of transitive dependencies;
- package-name confusion or typosquatting risk;
- version pinning, lockfile update, integrity hashes, and registry source;
- an exit or replacement strategy.

Do not add a package merely to avoid implementing a small, stable utility.

## Automated policy

The repository uses `.ai/config/dependency-policy.conf` and `.ai/tools/check-dependencies.sh`.

The gate checks:

- denied package names;
- explicitly allowed exceptions where a project uses allow-list mode;
- missing lockfiles for supported ecosystems;
- manifests in configured subdirectories and Python development groups;
- floating or wildcard versions in common manifests;
- vulnerable dependencies through available ecosystem scanners or OSV-Scanner;
- repository secrets, vulnerabilities, misconfiguration, and license risks through Trivy when installed;
- an optional organization-specific reputation scanner such as Socket through `DEPENDENCY_REPUTATION_CMD`.

Automated checks do not prove that a package is trustworthy. A newly published, abandoned, compromised, or malicious package may have no advisory yet.

## Deny-list rules

Add exact, case-sensitive package coordinates to `.ai/config/dependency-denylist.txt`, one per line:

```text
npm:left-pad
pypi:example-package
maven:group.id:artifact-id
cargo:example-crate
go:example.org/module
```

Blank lines and lines beginning with `#` are ignored. Every exception must include an owner, reason, and expiry in the review record. Do not silently remove a deny-list entry.

## Allow-list mode

For high-assurance projects, set `DEPENDENCY_ALLOWLIST_MODE=1` and populate `.ai/config/dependency-allowlist.txt`. All detected direct dependencies must then be listed. This is intentionally strict and normally unsuitable during early prototyping.

## Lockfiles and integrity

- Commit the ecosystem lockfile where supported.
- For Python use `uv.lock`, `poetry.lock`, `pdm.lock`, or the standardized `pylock.toml`; for .NET enable and commit `packages.lock.json`.
- CI must use frozen/locked installation modes.
- Do not regenerate lockfiles without reviewing the diff.
- Do not disable integrity or signature checks.
- Do not use mutable Git branches, unpinned URLs, or wildcard versions for production dependencies.
- Private registries and mirrors must be explicitly configured and documented.

Reproducibility is guaranteed by the committed lockfile, not by exact manifest
pins. Version ranges (for example `^1.2` or `>=1.0,<2`) in a manifest are
accepted as long as the required lockfile is present; the policy only rejects
genuinely unpinned specifiers (`*`, `latest`, `x`, empty, environment
interpolation) and remote or mutable sources. Projects that require exact
manifest pins should enforce that through their own linting in addition to this
baseline.

## Tool strategy

Preferred baseline:

1. `.ai/tools/dependency_policy.py` for local policy and lockfile checks.
2. OSV-Scanner for vulnerabilities across supported manifests and lockfiles.
3. Trivy for repository vulnerabilities, secrets, misconfiguration, and license classification.
4. Ecosystem-native scanners as defense in depth.
5. Optional organization-approved reputation tooling through `DEPENDENCY_REPUTATION_CMD`.

Do not automatically install scanning tools during verification. Install and pin them in the development environment or CI image.

## Review outcome

Block completion when:

- a denied or unapproved dependency is introduced;
- a required lockfile is absent;
- a critical/high vulnerability classified as P0/P1 remains unresolved; these findings cannot be waived;
- a forbidden, restricted, incompatible, or unknown license is unresolved;
- an install script, maintainer change, or package provenance concern is unexplained;
- the dependency is unnecessary or duplicates existing functionality.

Only lower-priority findings may receive a time-bounded exception with an authorized
owner, rationale, expiry, and follow-up.
