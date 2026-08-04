# T2 UI evidence decision

- Task: `T2-indexing-without-profiles`
- Date: 2026-08-04
- Decision: defer browser screenshot evidence for the full CHG-004 UI review to
  T4/T6.

## Rationale

T2 changes the transitional Import/Indizieren workflow and is covered by frontend
behavior tests for the affected states, including provider/model selection,
OpenAI confirmation, progress/list rendering, safe error messages, and delete
confirmation.

The active verification gate reports the browser procedure as not required for
the current implementation phase. Full revision-bound browser evidence for the
accepted design-class-3 screens remains required before final UI acceptance, when
the Cluster-Sets/Explorer UI slices are present and the end-to-end CHG-004
surface can be reviewed as one coherent workflow.

## Covered by automated checks in T2

- `frontend/src/App.test.tsx`
- `npm run test -- --run`
- `npm run lint`
- `npm run typecheck`
- `./.ai/tools/check-user-facing-errors.py`
- `./.ai/tools/check-ui-quality.py`

## Deferred browser states

- Project → Import desktop/mobile
- Project → Indizieren desktop/mobile
- empty/running/completed/failed/cancelled/deleted dataset states
- OpenAI cloud-confirmation state
