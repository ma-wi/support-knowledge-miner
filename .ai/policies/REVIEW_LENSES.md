# Conditional review routing

Load only guidance triggered by the change.

## Default baseline

- Always review acceptance criteria, tests, verification evidence, security impact, dependency impact, compatibility, and documentation impact.
- Load `SECURITY_GUIDELINES.md` when data, identity, files, network, commands, parsing, secrets, or irreversible change are involved.
- Load `DEPENDENCY_POLICY.md` when manifests, lockfiles, registries, package managers, or build-chain behavior change.
- Load `DOCUMENTATION_RULES.md` when user-facing docs, agent context, workflow state, architecture docs, or policy docs change.
- Request a specialist review only when the risk is significant or explicitly required.

| Trigger | Read | Required evidence |
|---|---|---|
| Trust boundaries, identity, data, parsing, networks, secrets, or irreversible change | `SECURITY_GUIDELINES.md`; optionally `.ai/templates/THREAT_MODEL.md` | Threat paths, negative tests, safe failure/recovery; specialist review for significant risk |
| Manifest, lockfile, registry, build-chain, or package change | `DEPENDENCY_POLICY.md` | Necessity/provenance/license review and `./.ai/tools/check-dependencies.sh` |
| Behavior, interface, migration, permission, or recovery change | `QUALITY_GATES.md` | Stable-seam tests, focused checks, and full verification |
| User, contributor, architecture, operational, ownership, or agent-context impact | `DOCUMENTATION_RULES.md`; optionally `.ai/templates/OWNERSHIP.md` | Current-state documentation, ownership evidence when needed, and `./.ai/tools/check-docs.py` |
