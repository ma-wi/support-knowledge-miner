# Ownership and review plan: <project or requirement>

- Status: draft | accepted | superseded
- Scope:
- Last updated:

Use this template when ownership is unclear, the project is complex, or branch
protection/review responsibility must be explicit before implementation.

## Decision owners

| Area | Authorized owner | Backup | Notes |
|---|---|---|---|
| Product requirements | | | |
| Architecture decisions | | | |
| Security/privacy risk acceptance | | | |
| Dependency exceptions | | | |
| Operations/release decisions | | | |

## Review ownership

| Change type | Required reviewer or group | Required evidence |
|---|---|---|
| Normal behavior change | | Requirement, tests, `./.ai/tools/verify.sh` |
| Significant architecture/API/migration change | | Specification, ADRs, verification, risk review |
| Security-sensitive change | | Threat model, negative tests, security review |
| Dependency/build-chain change | | Dependency review and scans |

## Repository controls

- Protected branches:
- Required CI checks:
- Required approval count:
- CODEOWNERS or equivalent:
- Secret scanning:
- Dependency/code scanning:
- Release authority:

## Acceptance

- Accepted by:
- Date:
- Conditions:
