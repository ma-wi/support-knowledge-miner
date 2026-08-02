# Support Knowledge Miner frontend

The React/Vite frontend is developed and verified through the repository wrappers.

```bash
npm ci
npm run dev
npm test
npm run lint
npm run build
```

Repository-native UI quality commands start their own loopback-only Vite instance,
block external browser requests, and write revision-bound evidence below the active
`.ai/work/<change-id>/evidence/ui/` directory:

```bash
npm run visual:evidence
npm run accessibility
npm run visual:regression
```

Visual baselines live in `ui-baselines/`. Updating them is an explicit review action
for an accepted visual change:

```bash
npm run visual:update-baselines
```
