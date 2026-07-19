# Conditional review routing

Load only guidance triggered by the change.

| Trigger | Read | Required evidence |
|---|---|---|
| Trust boundaries, identity, data, parsing, networks, secrets, or irreversible change | `SECURITY_GUIDELINES.md`; optionally `.ai/templates/THREAT_MODEL.md` | Threat paths, negative tests, safe failure/recovery; specialist review for significant risk |
| Manifest, lockfile, registry, build-chain, or package change | `DEPENDENCY_POLICY.md` | Necessity/provenance/license review and `./.ai/tools/check-dependencies.sh` |
| Behavior, interface, migration, permission, or recovery change | `QUALITY_GATES.md` | Stable-seam tests, focused checks, and full verification |
| User, contributor, architecture, operational, ownership, or agent-context impact | `DOCUMENTATION_RULES.md`; optionally `.ai/templates/OWNERSHIP.md` | Current-state documentation, ownership evidence when needed, and `./.ai/tools/check-docs.py` |
