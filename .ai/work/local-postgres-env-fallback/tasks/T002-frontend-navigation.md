# T002 frontend navigation

- Status: verified

## Scope

Replaced the single-page signed-in shell with three routed-by-state UI pages: projects/analyses as the default main page, provider/vLLM configuration, and user management. Provider/vLLM, user management, and sign-out are reachable through the profile menu; projects remain reachable as the primary navigation action.

## Verification

- `cd frontend && npm run format:check`: PASS
- `cd frontend && npm run lint`: PASS
- `cd frontend && npm run typecheck`: PASS
- `cd frontend && npm run test`: PASS, 9 tests
- `cd frontend && npm run build`: PASS
- `python .ai/tools/check-docs.py`: PASS
- `git diff --check`: PASS
