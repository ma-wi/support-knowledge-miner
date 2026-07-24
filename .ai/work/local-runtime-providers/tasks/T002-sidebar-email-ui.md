# T002 sidebar and email-login UI

- Status: verified

## Scope

Adapted the frontend shell to a left-sidebar layout aligned with the local reference application and the ma-wi.eu visual palette. Projects remain the main area. Settings are grouped into Embedding-Provider and Nutzer tabs. Project-specific workflows are grouped into tabs after a project is opened. The profile menu was removed.

User-facing login and user management now use email as the login identifier. The UI and public API responses no longer expose a separate username field. The database username column remains internal for compatibility and is synchronized to email on create/update.

## Verification

- `./.ai/tools/verify.sh`: PASS
