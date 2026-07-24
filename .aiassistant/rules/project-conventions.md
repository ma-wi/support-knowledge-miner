---
apply: always
---

# Project conventions

- Treat `AGENTS.md` as the binding instruction file for coding agents.
- Read `.ai/project.yaml` and only the applicable role or policy files.
- Use `.ai/policies/WORKFLOW.md` for behavioral or multi-file changes.
- For changes to existing capabilities, also use `.ai/policies/INCREMENTAL_CHANGE_WORKFLOW.md`; update capability specs in place and do not leave unexplained parallel or superseded behavior.
- Run `./.ai/tools/verify.sh` before claiming completion.
- Never access production; the prohibition in `AGENTS.md` is absolute.
