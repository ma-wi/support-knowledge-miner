# Design Delta

Use for design class 2 or 3. This is temporary; move only accepted current-state
rules to maintained design documentation.

## Metadata

- Change ID:
- Design class: 2 | 3
- Highest design class assigned: 2 | 3
- Implementation-start design class: not-started | 2 | 3
- Status: draft | ready-for-design-review | changes-requested | approved | superseded
- Affected capability specifications:
- Existing screens affected:
- Prototype strategy: storybook-composition | isolated-prototype
- Prototype artifact type: static-mockup | clickable-html-prototype | react-mock-prototype | storybook-composition | external-design-reference
- Prototype artifact or revision:
- Change base revision:
- Required visual gates:
- Decision owner:
- Last updated:

## Classification history

| Date | Previous class | New class | Reason | Approved by |
|---|---:|---:|---|---|
| | | | | |

## Problem and user outcome

## Current experience

## Desired experience

## User flow

## Screen inventory

| Screen or state | Existing | Changed | New | Notes |
|---|---:|---:|---:|---|
| | | | | |

## State inventory

For every state record required, not applicable with rationale, or the intended
behavior:

- default:
- loading:
- empty:
- error:
- validation:
- disabled:
- submitting:
- success:
- long content:
- small viewport:
- permission restricted:
- partial data:

## Responsive behavior

## Component impact

### Existing components reused

### Existing components extended

### New shared components

| Name/responsibility | Target path/layer | API/variants/states | Tests | Accessibility | Story/equivalent | Catalog entry |
|---|---|---|---|---|---|---|
| none | not-applicable | not-applicable | not-applicable | not-applicable | not-applicable | not-applicable |

### New feature-local components

### Components replaced or removed

### Rejected reuse options

### Rationale

## Design-system impact

- docs/design/DESIGN_SYSTEM.md impact:
- docs/design/COMPONENT_CATALOG.md impact:
- Tokens:
- Accessibility:
- Responsive behavior:
- Existing-screen/component migration:
- Project-wide visual-regression impact:

## Accessibility requirements

## Error experience

### Action and failure inventory

| Action | Failure | Error code | User message | Placement | Recovery action |
|---|---|---|---|---|---|
| | | | | | |

### Error presentation levels

- Inline field error:
- Form-level banner:
- Component-level error:
- Page-level error:
- Toast or transient notification:
- Fatal application fallback:

### Input preservation

Describe whether entered values, filters, selections, and unsaved changes remain
available after each failure.

### Focus behavior

- Field validation failure:
- Form submission failure:
- Page-level load failure:
- Dialog action failure:

### Recovery behavior

- Retry:
- Reload:
- Reauthenticate:
- Return to previous page:
- Contact support:
- Resolve conflict:
- Correct input:

### Unknown error fallback

- User-facing title:
- User-facing explanation:
- Correlation ID placement:
- Support instruction:
- Input preservation:
- Retry behavior:

### Error-state evidence

- Mockup:
- Prototype:
- Storybook:
- Browser screenshots:

For design class 2 or 3, every relevant central action must show its error states in
the approved artifact before `Status: approved`.

## Prototype or mockup plan

## Prototype isolation

- Production imports allowed: no
- Production build inclusion allowed: no
- Production backend connection allowed: no
- Production runtime dependency allowed: no
- Mock data or local fixtures:
- Private and non-deployable:
- Required tool dependencies and owning package:

## Mockup or prototype evidence

## Prototype promotion decisions

Use `reuse-existing-production-component`, `extend-existing-production-component`,
`create-design-system-component`, `create-feature-local-component`,
`implement-page-composition`, or `discard-prototype-only-code`.

| Prototype element | Decision | Target path | Target layer/responsibility | Tests | Story | Accessibility | Catalog update |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

## Open design decisions

## Approval

- Decision: pending | changes-requested | approved | superseded
- Approved direction:
- Approved artifact or revision:
- Approval type: human | design-owner
- Approved by:
- Date:
