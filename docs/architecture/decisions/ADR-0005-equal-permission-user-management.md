# ADR-0005: Equal-permission local user management

- Status: accepted
- Date: 2026-07-19
- Owners: User
- Related requirement: support-knowledge-miner-mvp1
- External reference identifiers: none

## Context

The MVP was initially scoped as a single local-user application. The Decision Owner added simple user management so multiple local users can sign in and actions can be attributed to a real user. The application is still local-first and does not need differentiated roles or organization-wide approval workflows.

## Decision

Implement simple authentication and equal-permission user management. Each user has username, first name, last name, email, and password hash. Passwords are never stored or returned as plaintext. All authenticated users have the same permissions. Any authenticated user may create another user, edit another user's username/name/email, set or change another user's password, and delete another user. A user may not delete themselves.

Create the initial user once through environment variables, local configuration, or database seed/migration. Persist acting user identity on auditable actions.

## Alternatives considered

- Single local user only: rejected because action attribution and shared local use are required.
- Full role-based access control: rejected because all MVP users are intentionally equal and a role workflow would expand scope.
- Storing plaintext passwords: rejected as an avoidable security vulnerability.

## Consequences

### Positive

- Enables local multi-user access without a complex role model.
- Provides real actor identity for audit events.
- Keeps user administration simple and explicit.

### Negative

- Any user can change another user's account and password, so this is not suitable for untrusted multi-tenant deployment.
- Authentication/session handling and password hashing add security-sensitive implementation requirements.

### Risks and mitigations

- Risk: password exposure.
- Mitigation: store only password hashes with an established password-hashing algorithm and never return hashes/passwords through normal read APIs.

- Risk: all users are effectively administrators.
- Mitigation: document this as an intentional local MVP constraint and keep server/multi-tenant deployment out of scope.

- Risk: account lockout if the only user is deleted.
- Mitigation: prohibit self-delete; initial-user seed can create the first user when no users exist.

## Validation

- Authentication tests cover valid and invalid sign-in.
- User-management tests cover create, edit, password reset/change, delete other user, and self-delete denial.
- Persistence tests verify password hashes are stored instead of plaintext.
- Audit tests verify protected actions record acting user identity.
