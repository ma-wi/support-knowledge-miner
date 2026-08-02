---
apply: always
---

# Project conventions

- Treat `AGENTS.md` as the binding instruction file for coding agents.
- When `project.name` is `CHANGE_ME` and the template-only copy/verification scripts
  exist, use the template-maintenance mode in `AGENTS.md`; template policies and
  examples are artifacts under review.
- Read `.ai/project.yaml` and only the applicable role or policy files.
- Use `.ai/policies/WORKFLOW.md` for behavioral or multi-file changes.
- For changes to existing capabilities, also use `.ai/policies/INCREMENTAL_CHANGE_WORKFLOW.md`; update capability specs in place and do not leave unexplained parallel or superseded behavior.
- Run `./.ai/tools/verify.sh` before claiming completion.
- Never access production; the prohibition in `AGENTS.md` is absolute.
