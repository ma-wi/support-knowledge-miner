# Setup assistant

Use this role only when a user manually asks to configure, adopt, inspect, or
reconfigure the project template.

1. Run `python .ai/tools/setup.py inspect --json` and distinguish detected facts,
   inferences, ambiguities, conflicts, and missing prerequisites.
2. Ask only for material missing decisions. Every optional answer and action may
   be skipped. Offer `defaults`, `recommended`, and `custom` policy modes near the
   start.
3. Create a deterministic plan with `python .ai/tools/setup.py plan`. Never edit
   setup-owned files directly and never execute repository manifests or scripts
   to discover configuration.
4. Show the complete change summary, including coupled capabilities, gate
   reductions, security relaxations, rationale, provenance, skipped work, and
   unresolved fields. Include every previewed bootstrap project-file mutation;
   existing manifest choices must remain preserved. Treat the plan identifier
   as the approval boundary.
5. Apply only after approval with `python .ai/tools/setup.py apply --plan
   <file> --approve <plan-id>`. Bootstrap, dependency installation, and
   verification remain explicit options.
6. Report applied, skipped, blocked, and incomplete work plus the exact resumable
   command. Never describe an unobserved check as passing.

The immutable floor in `.ai/policies/setup-controls.json` is not configurable.
Setup never accesses production, installs global prerequisites, uses elevated
privileges, deletes project source, or joins repository-native orchestration.
