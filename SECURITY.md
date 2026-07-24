# Security Policy

## Supported Scope

Support Knowledge Miner MVP 1 is local-only. Server deployment, production operations, production data, production credentials, and production-control paths are out of scope.

## Reporting

Report security issues through the project issue or pull-request workflow available to the repository maintainers. Do not include secrets, production data, customer data, or sensitive personal data in reports. Use minimal synthetic reproduction data.

## Security Expectations

- Never connect the application, tests, scripts, or diagnostics to production resources.
- Use only local, development, test, or sandbox resources with no production data.
- Store passwords only as hashes.
- Treat OpenAI keys as write-only secrets after save.
- Treat imported text and original-text exports as potentially sensitive.
- Run `./.ai/tools/verify.sh` before merging changes.
