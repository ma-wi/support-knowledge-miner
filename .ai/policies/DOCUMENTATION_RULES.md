# Documentation rules

## Principle

Document current truth, durable rationale, and actionable next steps. Do not document agent reasoning, chat transcripts, tool logs, or a chronological work diary.

## Default baseline

- `README.md` explains the current project for humans.
- `.ai/PROJECT_CONTEXT.md` gives agents a compact map of the project.
- `SECURITY.md` documents the real security reporting process before CI is expected to pass.
- `.ai/NEXT_STEPS.md` contains only short-term unresolved follow-up.
- `CHANGELOG.md` is created only when the project has an actual release process.
- Temporary `.ai/work/` files stay until review is complete, then durable facts are moved to maintained documentation.

## Language and spelling

In German-language documentation, write German umlauts directly as `ä`, `ö`, and `ü`. Do not replace them with `ae`, `oe`, or `ue` unless a technical identifier, command, file path, or external proper name requires ASCII.

## Canonical information classes

- Binding rules: `AGENTS.md`, `.aiassistant/rules/`, quality and security policies.
- Durable product behavior: accepted requirements and capability-based current-state documents in `docs/specifications/`.
- Current project truth: `README.md`, `PROJECT_CONTEXT.md`, and architecture or operations documentation.
- Durable rationale: ADRs.
- Active temporary work: `.ai/work/<requirement-or-change-id>/`.
- Short-term follow-up: `NEXT_STEPS.md`; long-term work belongs in issues.
- Historical chronology: Git, pull requests, releases, and user-visible changelog entries.

Each fact should have one canonical location. Other files should link to it instead of copying large sections.

## Audience separation

- `README.md`: users and new human contributors.
- `docs/architecture/`: durable system design and ADRs.
- `.ai/`: compact agent context, workflow, active work, and templates.
- `CHANGELOG.md`: create it when the project has a defined release and versioning process.

## Update triggers

Review and update documentation after a completed meaningful change when it affects behavior, interfaces, configuration, architecture, security, operation, deployment, monitoring, supported environments, or contributor workflow. Do not edit documentation merely because a file was touched.

For implementation work, `README.md` and `.ai/PROJECT_CONTEXT.md` are mandatory review targets after every implemented change. Update `README.md` for human-facing current truth such as purpose, setup, commands, usage, configuration, operations, and contributor workflow. Update `.ai/PROJECT_CONTEXT.md` for agent-facing current truth such as project purpose, stack, architecture map, repository conventions, quality commands, constraints, risks, and high-value references. When no relevant update is needed, record that explicit assessment in the active task or plan evidence.

## Capturing chat instructions

Classify relevant user instructions before closeout. Persist only accepted requirements, durable rules, decisions, constraints, and actionable future work. Keep task-only instructions in the temporary work directory. When unsure, record an assumption or open question instead of silently making it permanent. Never store complete conversations.

## Context and size budgets

Budgets are configured under `documentation.budgets` in `.ai/project.yaml` and checked by `.ai/tools/check-docs.py`. They are warning thresholds that trigger curation. Do not remove necessary information solely to satisfy a number.

- Keep root `AGENTS.md` concise and link to detailed policies.
- Keep `PROJECT_CONTEXT.md` as a system map, not a source-code walkthrough.
- Keep `CURRENT_PLAN.md` as a small pointer to active work.
- Keep `NEXT_STEPS.md` short, prioritized, and free of completed items.
- Keep work-item files focused on one independently verifiable task.
- Summarize adopted MCP guidance; never paste broad retrieved passages.

## Replacement and history

Update current-state documents in place and remove obsolete statements. Capability
specifications are named by durable capability rather than change ID; incremental
changes update them in place and must not append a chronological delta. When a durable decision changes, mark the old ADR as superseded and create or link the replacement. Use Git, issues, pull requests, and releases for history instead of retaining completed task files or narrative logs.

## Curation cadence

Apply the documentation review lens:

- during closeout of significant requirements;
- before releases when configured;
- after major architecture, security, or stack changes;
- when `.ai/tools/check-docs.py` reports budget or consistency warnings;
- when documents conflict or ownership is unclear.

Curation occurs before temporary work artifacts are removed. It is normally part of the independent reviewer and closeout flow; use another specialist context only when the documentation surface is unusually large or risky.
