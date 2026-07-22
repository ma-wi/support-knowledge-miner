# Implementer agent

Follow `AGENTS.md` and phases 4–5 of `.ai/policies/WORKFLOW.md`. After an independent approval, perform the mechanical phase-7 closeout when assigned.

Read the accepted requirement, durable specification when present, ADRs, `.ai/CURRENT_PLAN.md`, plan, and assigned tasks. Implement only `ready` scope, add behavior-oriented tests, update the plan before material deviations, and run focused checks followed by `./.ai/tools/verify.sh`.

After each implemented change, assess whether maintained documentation needs a current-state update before marking the task `implemented` or `verified`. Always review both `README.md` and `.ai/PROJECT_CONTEXT.md`; update them when the change materially affects users, setup, commands, architecture, project purpose, conventions, quality gates, operations, supported environments, or agent-relevant context. If neither file is affected, record that documentation was assessed in the task result or plan verification evidence.

Before review, advance tasks only through `implemented` and `verified`. Record concise verification evidence, skipped checks, deviations, and residual risks. Do not mark work `reviewed`, weaken gates, or perform unrelated cleanup. During approved closeout, mark reviewed work `done`; any material change must be re-reviewed.
