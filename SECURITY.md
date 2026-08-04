# Security

## Reporting a vulnerability

Report suspected vulnerabilities privately to: mathias.wilhelm@ma-wi.eu

Do not open a public issue for an unpatched vulnerability. Include the affected
version or revision, reproduction steps using non-production data, expected impact,
and any known mitigations. Do not send credentials, secrets, production data, or
sensitive personal data.

## Response expectations

- Acknowledgement target: Within 7 calendar days.
- Triage target: Within 14 calendar days.
- Supported versions: Only the latest revision of the main branch.
- Disclosure and coordination process: Coordinate disclosure privately with the maintainer. Public disclosure occurs only after a fix or mitigation is available.

<!-- guided-setup:policy-profile:start -->
## Guided setup policy profile

- Decision mode: `recommended`
- Risk profile: `public-service-review`
- Decisions:
  - `authentication` = `required` (assistant-recommendation): Network service evidence may include protected operations
  - `availability` = `required` (assistant-recommendation): Network service or external input evidence was detected
  - `dependency_scanning` = `required` (assistant-recommendation): Dependency manifests were detected
  - `dependency_vulnerability_threshold` = `high` (assistant-recommendation): Retain the versioned high-severity blocking baseline
  - `secret_scanning` = `required` (assistant-recommendation): Dependencies, deployment, or network exposure can carry secrets
  - `static_security` = `required` (assistant-recommendation): Supported code or external inputs need static security analysis
  - `warning_treatment` = `errors` (assistant-recommendation): Detected code should keep warnings actionable
- Canonical structured source: `.ai/policy-profile.yaml`
<!-- guided-setup:policy-profile:end -->
