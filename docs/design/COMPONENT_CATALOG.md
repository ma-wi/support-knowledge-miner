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
| App shell | page composition | Auth gate, top-right global menu, settings/project workspace and global feedback | `frontend/src/App.tsx`, `frontend/src/App.css` | Whole local MVP application | React state and route-like tab state | signed-out, session-checking, signed-in, feedback states, no persistent left global sidebar | Main/region headings, menu button with Escape close/focus return and alert/status feedback | Browser evidence manifest | Monolithic until a shared component split is accepted | Split only along stable workflow boundaries | active | not-applicable |
| Project tabs | feature-local components | Project workflow navigation | `frontend/src/App.tsx` | Open project workspace only | `projectTab` state | Import, Indizieren, Cluster-Sets, Explorer, Einstellungen | Buttons with selected state | App tests and browser evidence | Not a router | Extend only with accepted workflow tabs | active | not-applicable |
| Provider forms | feature-local components | Configure OpenAI/Ollama provider instances with available models and embedding/LLM allow-lists | `frontend/src/App.tsx` | Settings page | Form submit handlers | local/cloud, add/remove/connection-test/discover/pull/save, write-only key | Labeled fields and safe feedback | App tests | No shared form abstraction yet | Extract only if repeated outside settings | active | not-applicable |
| Import panels | feature-local components | Import upload, logs and skipped-row detail | `frontend/src/App.tsx` | Import tab | Import log state | empty, completed, failed, deleted dataset | Regions, forms, status/error text | App tests | Uses project-local list/card styling | Extend in place for import-only states | active | not-applicable |
| Indexing list | feature-local components | Start/list/cancel/delete indexing jobs, including optional provider-input line-break/lowercase normalization | `frontend/src/App.tsx` | Indizieren tab | Indexing run state and polling | queued/running/completed/failed/cancelled/deleted; preserve/remove/replace line breaks; optional lowercase | Progress elements, safe diagnostics, bounded replacement input and checkbox normalization controls | App tests | No background-job shared component yet | Extract only after another job list needs same API | active | not-applicable |
| Cluster-Set tree cards | feature-local components | Show saved root/child Cluster-Sets, status, lineage and allowed actions including Summary-regeneration dialog entry | `frontend/src/App.tsx`, `frontend/src/App.css` | Cluster-Sets tab | ClusterSet data, parent/child relation | completed/running/deleted-history, load/refine/summary-dialog/cancel/delete | Card headings, progress, disabled invalid actions | Browser evidence | Tree expand/fold is currently represented by nested cards | Add explicit disclosure only with accepted design | active | not-applicable |
| Explorer table | feature-local components | Primary analyst comparison surface for loaded Cluster rows | `frontend/src/App.tsx`, `frontend/src/App.css` | Explorer tab | Loaded ClusterSet, Cluster rows, filter and sort state | loaded, no-result, grouped, outlier, excluded, mismatch, ascending/descending/unsorted | Semantic table with labeled controls and `aria-sort` on sortable headers | App tests and browser evidence | Wide table scrolls horizontally on mobile; sorting is client-side over loaded rows | Extend in place for Explorer-only columns | active | not-applicable |
| Source dialog | feature-local components | Inspect original source pairs for one Cluster | `frontend/src/App.tsx`, `frontend/src/App.css` | Explorer table action | Source rows loaded by cluster and optional project ticket URL template | loading, empty, loaded, safe failure, ticket-link/plain-ticket | Modal dialog, sticky header, focus trap, Escape/close/backdrop close, focus return, safe external link attrs | App tests and browser evidence | Paged by explicit load-more; no source search yet | Add pagination/search before large-source production use | active | not-applicable |
| Explorer control rail | feature-local components | Collapsible left-side Explorer controls for Cluster-Set switching, search/filter, outliers, Summary regeneration and export/history/content | `frontend/src/App.tsx`, `frontend/src/App.css` | Explorer tab loaded state | Loaded ClusterSet, filter state, export format/logs, Summary action state and collapse state | loaded, collapsed, expanded, no-result, Summary disabled/error, export disabled/error, CSV/JSON, history, last content | Labeled sections before the table; icon-only collapse button exposes expanded state; errors render in rail/dialog surfaces | App tests and browser evidence | Rail follows page scroll; table workspace owns large-list vertical scrolling; does not export raw source-dialog text; Summary version/copy modes are absent until accepted | Raw export or Summary versioning requires separate accepted component/state | active | replaces right-side Explorer export panel |
| Feedback message | design-system feedback | Distinguish success/info/warning/error in a global overlay | `frontend/src/App.tsx`, `frontend/src/App.css` | App-wide | `kind`, safe message text, close action | status vs alert, auto-dismiss, manual close | `role=status` or `role=alert` with close button | App tests | Global overlay only, not field-level association | Add field-level errors only with form-specific tests | active | not-applicable |

Allowed status values are `active`, `deprecated`, and `experimental`. A deprecated
component names its replacement and removal criterion. A new shared component must
be catalogued in the same change that introduces it.
