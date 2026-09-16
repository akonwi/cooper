# Backlog: retained custom controls in CUI

Status: deferred until a concrete use case appears. No API is committed to.

## When to revisit

Revisit when an application needs to embed a retained Cooper control that cannot
reasonably be composed from existing CUI views: a custom-painted chart, a
specialized editor, a third-party widget, or an existing imperative control.

Ordinary custom UI should use a CUI `Component` composed from existing views.
The supported built-in controls already have CUI constructors, so there is no
immediate gap requiring a generic adapter.

## Candidate approach

Provide a reusable adapter defined once per retained control type. Components
would describe props and an optional key, not own control instances. CUI would
create, update, attach, reconcile, and destroy those instances.

Proposed contracts to evaluate against the first real integration:

- Identity is adapter plus key, or position when unkeyed. Changing adapters
  replaces the instance, even if both adapters return the same control type.
- The control satisfies Cooper's retained-control contract; CUI handles
  framework-internal type erasure and attachment.
- Destruction uses control-specific cleanup. Generic node destruction is not
  sufficient for every control.
- The control is an opaque leaf to CUI. It may own internal retained children;
  accepting CUI-managed children would require a separate container contract.
- Event listeners register once, see current props rather than stale callbacks,
  and trigger component-local updates. Their lifetime follows the mounted control.

The adapter's exact API and Ard generic inference remain unverified. Before
adopting an API, prove it with a concrete control and cover read-only and
interactive behavior, keyed reordering, adapter replacement, current callback
delivery, and teardown. Keep the integration code with the control author rather
than requiring boilerplate at every application call site.
