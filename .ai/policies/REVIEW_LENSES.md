# Conditional review routing

Load only guidance triggered by the change.

## Default baseline

- Always review acceptance criteria, tests, verification evidence, security impact, dependency impact, compatibility, and documentation impact.
- Load `SECURITY_GUIDELINES.md` when data, identity, files, network, commands, parsing, secrets, or irreversible change are involved.
- Load `DEPENDENCY_POLICY.md` when manifests, lockfiles, registries, package managers, or build-chain behavior change.
- Load `DOCUMENTATION_RULES.md` when user-facing docs, agent context, workflow state, architecture docs, or policy docs change.
- Request a specialist review only when the risk is significant or explicitly required.
- Use the work-item Security Assurance as the shared planner/implementer/reviewer
  record. Review routing against the actual change; a `not-required` declaration is
  not authoritative when a trigger below applies.

| Trigger | Read | Required evidence |
|---|---|---|
| Trust boundaries, identity, data, parsing, networks, secrets, or irreversible change | `SECURITY_GUIDELINES.md`; optionally `.ai/templates/THREAT_MODEL.md` | Threat paths, negative tests, safe failure/recovery; specialist review for significant risk |
| Manifest, lockfile, registry, build-chain, or package change | `DEPENDENCY_POLICY.md` | Necessity/provenance/license review and `./.ai/tools/check-dependencies.sh` |
| Existing behavior, interface, domain concept, migration, deprecation, removal, permission, or recovery change | `INCREMENTAL_CHANGE_WORKFLOW.md`; `QUALITY_GATES.md` | Accepted desired end state, complete impact matrix, vertical slices, superseded-artifact evidence, stable-seam tests, and full verification |
| User, contributor, architecture, operational, ownership, or agent-context impact | `DOCUMENTATION_RULES.md`; optionally `.ai/templates/OWNERSHIP.md` | Current-state documentation, ownership evidence when needed, and `./.ai/tools/check-docs.py` |
| Enabled user-facing error handling and a changed user-triggered or user-observable action | `USER_FACING_ERROR_HANDLING.md`; add API/frontend supplements only for affected enabled surfaces | Complete action matrix, stable catalogued codes, recovery, preservation, negative tests, and applicable mappings |
| Enabled UI quality and user-interface impact | `UI_QUALITY.md`; add prototype supplement for class 2/3 artifact work and visual supplement for class 1–3 evidence | Valid design class, reuse decision, approval, isolation, revision-bound evidence, and independent visual review as applicable |
| Orchestrator, agent execution, queue/checkpoint state, owner gates, or role transitions | `ORCHESTRATION.md`; `SECURITY_GUIDELINES.md` | Trust boundaries, role-write isolation, authenticated owner path, fail-closed parsing, bounded resources, resume/idempotency, and bypass-focused negative tests |
