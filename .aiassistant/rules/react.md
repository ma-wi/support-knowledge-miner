---
apply: by-file-patterns
patterns: ["**/*.ts", "**/*.tsx", "**/*.js", "**/*.jsx", "**/package.json"]
---

# React and TypeScript rules

Apply to React, TypeScript, JavaScript, and frontend configuration.

- Prefer TypeScript with strict checking.
- Keep components focused and move reusable behavior into tested hooks or services.
- Do not place secrets or privileged decisions in frontend code.
- Validate server responses and handle loading, empty, error, and permission states.
- When user-facing error and frontend handling are enabled and an affected action is
  user-triggered or user-observable, follow the core and frontend error policies.
- Preserve accessibility: semantic elements, labels, keyboard operation, focus behavior, and test coverage.
- When UI quality is enabled and the change has UI impact, follow
  `.ai/policies/UI_QUALITY.md`, reuse the configured component foundation, and keep
  temporary prototypes outside production dependencies.
- Use the configured package manager and committed lockfile.
- Run lint, type checking, tests, build, and dependency audit before completion.
