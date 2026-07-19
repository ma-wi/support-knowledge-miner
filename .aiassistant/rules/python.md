# Python rules

Apply to Python code and Python project configuration.

- Prefer Python 3.12+ unless the project configuration says otherwise.
- Use type hints for public and non-trivial internal APIs.
- Prefer Ruff for formatting and linting, pytest for tests, mypy for static typing, and Bandit plus pip-audit for security checks.
- Keep domain logic independent from framework and transport layers.
- Validate untrusted input at boundaries.
- Avoid mutable default arguments, broad exception catches, hidden global state, and import-time side effects.
- Add regression tests for bug fixes and negative tests for permission or validation behavior.
