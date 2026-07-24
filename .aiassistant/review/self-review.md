# AI Self-Review rules

Review selected changes against `AGENTS.md`, `.ai/project.yaml`, the active requirement, durable specification, `.ai/CURRENT_PLAN.md`, its referenced `PLAN.md` and work-item files, applicable ADRs, and repository quality policies.

Check for unmet acceptance criteria, regressions, incompatible API/schema/configuration changes, missing tests, security defects, risky dependencies, Python typing and error handling, React accessibility and client-side trust, Bash/PowerShell quoting and error propagation, .NET/VB analyzer and compatibility defects, stale documentation, unrelated changes, and unnecessary complexity. For incremental work, verify the accepted desired end state across every applicable layer, complete impact classification, existing-responsibility reuse, removal or tracking of superseded artifacts, and current capability specifications.

Reject any proposed agent action or verification step that accesses production or could execute against or affect production. Check changes for accidental automatic production effects. Deployment or operations artifacts may be prepared for later controlled use by authorized humans, but agents must not execute them against production or wire ordinary development actions to trigger production. Confirm examples and verification steps use explicitly non-production targets and non-production data; ambiguity is a failure.

Severity:

- `P0`: immediate critical risk, exploitable vulnerability, or data loss.
- `P1`: must be fixed before merge.
- `P2`: should be fixed.
- `P3`: optional improvement.

Reference concrete files and locations, explain impact, separate defects from preferences, and never invent successful test or scanner results.


## Documentation integrity

Check whether durable user instructions were captured in requirements, specifications, ADRs, or maintained documentation; whether temporary work leaked into permanent documentation; and whether obsolete or duplicate guidance should be removed. Consider documentation-budget warnings from `./.ai/tools/check-docs.py`.
