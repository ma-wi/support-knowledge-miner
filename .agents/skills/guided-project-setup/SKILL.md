---
name: guided-project-setup
description: Manually inspect, configure, adopt, diagnose, or reconfigure a project that uses this template through its deterministic setup engine.
---

# Guided project setup

Read `.ai/roles/SETUP_ASSISTANT.md` and follow it. Use
`.ai/tools/setup.py` as the only owner of inspection, planning, policy
reconciliation, and configuration mutation.

For a health check, run `python .ai/tools/setup.py doctor --json`. For initial
setup or reconfiguration, inspect first, create a reviewable plan, and apply only
the exact approved plan identifier. Do not run bootstrap, installation, or
verification unless the user selects it.
