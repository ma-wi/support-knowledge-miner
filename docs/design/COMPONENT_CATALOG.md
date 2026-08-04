# Component catalog

This is the current inventory of reusable UI responsibilities. It is not a change
log.

Supported layers:

```text
design-system primitives
design-system forms
design-system layout
design-system feedback
shared application components
feature-local components
page composition
```

## Components

| Name | Layer | Responsibility | Source path | Allowed use | Important API/props | Variants and states | Accessibility | Story/example | Limitations | Extension | Status | Replacement |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| App shell | page composition | Auth gate, sidebar, settings/project workspace and global feedback | `frontend/src/App.tsx`, `frontend/src/App.css` | Whole local MVP application | React state and route-like tab state | signed-out, session-checking, signed-in, feedback states | Main/nav/region headings and alert/status feedback | Browser evidence manifest | Monolithic until a shared component split is accepted | Split only along stable workflow boundaries | active | not-applicable |
| Project tabs | feature-local components | Project workflow navigation | `frontend/src/App.tsx` | Open project workspace only | `projectTab` state | Import, Indizieren, Cluster-Sets, Explorer, Projekt löschen | Buttons with selected state | App tests and browser evidence | Not a router | Extend only with accepted workflow tabs | active | not-applicable |
| Provider forms | feature-local components | Configure OpenAI/Ollama/vLLM embedding and LLM providers | `frontend/src/App.tsx` | Settings page | Form submit handlers | local/cloud, check/pull/save, write-only key | Labeled fields and safe feedback | App tests | No shared form abstraction yet | Extract only if repeated outside settings | active | not-applicable |
| Import panels | feature-local components | Import upload, logs and skipped-row detail | `frontend/src/App.tsx` | Import tab | Import log state | empty, completed, failed, deleted dataset | Regions, forms, status/error text | App tests | Uses project-local list/card styling | Extend in place for import-only states | active | not-applicable |
| Indexing list | feature-local components | Start/list/cancel/delete indexing jobs | `frontend/src/App.tsx` | Indizieren tab | Indexing run state and polling | queued/running/completed/failed/cancelled/deleted | Progress elements and safe diagnostics | App tests | No background-job shared component yet | Extract only after another job list needs same API | active | not-applicable |
| Cluster-Set tree cards | feature-local components | Show saved root/child Cluster-Sets, status, lineage and allowed actions | `frontend/src/App.tsx`, `frontend/src/App.css` | Cluster-Sets tab | ClusterSet data, parent/child relation | completed/running/deleted-history, load/refine/cancel/delete | Card headings, progress, disabled invalid actions | Browser evidence | Tree expand/fold is currently represented by nested cards | Add explicit disclosure only with accepted design | active | not-applicable |
| Explorer table | feature-local components | Primary analyst comparison surface for loaded Cluster rows | `frontend/src/App.tsx`, `frontend/src/App.css` | Explorer tab | Loaded ClusterSet and Cluster rows | loaded, no-result, grouped, outlier, excluded, mismatch | Semantic table with labeled controls | App tests and browser evidence | Wide table scrolls horizontally on mobile | Extend in place for Explorer-only columns | active | not-applicable |
| Source dialog | feature-local components | Inspect original source pairs for one Cluster | `frontend/src/App.tsx`, `frontend/src/App.css` | Explorer table action | Source rows loaded by cluster | loading, empty, loaded, safe failure | Modal dialog, focus trap, Escape/close, focus return | App tests and browser evidence | No pagination yet for very large clusters | Add pagination/search before large-source production use | active | not-applicable |
| Explorer export panel | feature-local components | Export current filtered Explorer table and show history/content | `frontend/src/App.tsx`, `frontend/src/App.css` | Explorer tab only | Export format, visible rows, export logs | disabled without set/rows, CSV/JSON, history, last content | Labeled form and history region | App tests and browser evidence | Does not export raw source-dialog text | Raw export requires separate accepted component/state | active | not-applicable |
| Feedback message | design-system feedback | Distinguish success/info/warning/error at current action surface | `frontend/src/App.tsx`, `frontend/src/App.css` | App-wide | `kind`, safe message text | status vs alert | `role=status` or `role=alert` | App tests | Global message only, not field-level association | Add field-level errors only with form-specific tests | active | not-applicable |

Allowed status values are `active`, `deprecated`, and `experimental`. A deprecated
component names its replacement and removal criterion. A new shared component must
be catalogued in the same change that introduces it.
