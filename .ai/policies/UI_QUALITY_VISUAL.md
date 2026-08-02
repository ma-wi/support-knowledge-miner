# UI browser evidence and visual review

Load this supplement for design class 1–3 browser evidence or visual review. Also
follow `UI_QUALITY.md`.

## Evidence

Store temporary evidence under `.ai/work/<change-id>/evidence/ui/`:

```text
manifest.json
desktop/
mobile/
accessibility/
reports/
```

The manifest records change ID, timestamp, full Git revision, working-tree
fingerprint, browser/version, reviewed URL, execution mode, performer, and every
screen/state/viewport/file. Screenshots are non-empty PNG, JPEG, or WebP with matching
file signatures.

Default viewports are desktop `1440x1000` and mobile `390x844`; configured projects
may replace them. Evidence covers relevant loading, empty, validation, permission,
conflict, business-rule, network, timeout, unexpected, long-message, partial-data,
responsive, focus, keyboard, retained-input, recovery, and no-false-success states.

A manual gate records `interaction_check: passed` and concrete accessibility
observations when accessibility is enabled without a command. Automated evidence
records the configured command and passing result. Missing browser automation uses
the configured manual fallback or fails; it is never described as automated.

The fingerprint binds evidence to production changes while excluding the active work
directory. Production changes invalidate earlier evidence and approval. Screenshots
do not replace interaction tests, and static mockups never prove production behavior.

## Independent visual review

Code and visual review are separate. Follow `.ai/roles/VISUAL_REVIEWER.md`. The report
at `evidence/ui/reports/visual-review.json` uses verdict `approved`,
`changes_requested`, `requires_human_decision`, or `invalid_review`.

Findings include ID, severity, action when applicable, screen, state, viewport,
evidence, problem, expected behavior, and required change. Subjective preferences
without an accepted rule or observable defect are invalid.

After remediation, regenerate affected evidence. A material deviation from approved
design returns to design review. Required browser or visual work cannot be replaced
by code inspection, unit tests, or an unavailable-environment skip.

## Closeout

Delete change-specific evidence by default after durable facts are curated. Retained
evidence needs an explicit policy, purpose, and owner. Complete the visual-review
verdict before tasks advance beyond `verified`.
