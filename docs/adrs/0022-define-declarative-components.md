# 0022: Define declarative components

## Status

Proposed. An experimental implementation and executable example are available;
the imperative Cooper contract remains unchanged.

## Context

Applications need persistent component structs, ordinary mutable state and
props, optional lifecycle methods, and declarative reconciliation without hooks,
generated declarations, or framework props holders.

An earlier design made authors explicitly retain children and bind nested
lifetimes to construction-time ownership objects. That exposed bookkeeping which
the renderer can derive from the expanded view, complicated composition, and
made removal semantics depend on author-managed state. The prototype instead
tests automatic renderer ownership and snapshot-based identity.

## Decision

Add the opt-in `cooper/cui` namespace. Every component implements
`fn mut render() View`. `child(create, props, key:)` infers concrete component
and props types; props are supplied as an ordinary value, and the constructor's
mutable props reference is updated before retained renders. Construction occurs
only on mount.

`mount(app, View)` accepts a primitive or component root and uses the App's
Runtime and Root. The renderer
automatically owns nested components found while expanding child lists. Within a
retained parent, key plus concrete component type plus props type defines keyed
identity; unkeyed position plus those types defines unkeyed identity. Factory
function identity is not compared. Consequently, different factories producing
the same component and props types retain the instance and do not rerun an
initializer. A removal and reinsertion coalesced before commit retains identity;
reinsertion after a committed removal creates a fresh instance.

The optional `Lifecycle` trait provides `mounted(ctx: Context)` and `unmounting(ctx: Context)`. Mount hooks
run child-first after refs and controls attach, without guaranteeing layout.
Hook mutations schedule one follow-up render. Retirement first cancels every
callback in the subtree, then disposes controls and calls unmount hooks child-first.
Components acquire external resources in `mounted` and release their own resources
in `unmounting`; the framework owns component children and mount-scoped dispatch.

All built-in event callbacks receive `Context` as their final argument. Primitive
views inherit their nearest component context, or the renderer context outside
components. Component contexts exist independently of lifecycle hooks; render
remains context-free. This avoids stored context and bound-function workarounds.

Components own ordinary `async::start` workers. `Context.dispatch` queues UI-thread
callbacks, checks mount lifetime at posting and execution, and invalidates after
delivery. `Context.cancellation` closes before cleanup. Retired handles reject new
work and suppress queued callbacks, including after reinsertion. Cancellation of
the worker itself is cooperative. Per-request supersession belongs to application
code. This replaces the experimental `Tasks.after` timer API.

Managed events coalesce a root render. `Renderer.update` and `invalidate` are
UI-thread APIs. `dispatch` is background-safe but guards work only with the
renderer lifetime; component workers use mount-scoped dispatch instead.

The renderer reconciles text, input, box, and scrolling views onto existing
Cooper controls. It validates duplicate sibling keys and refs across expanded
components before mutating controls or refs. Programmer exceptions have no
transactional rollback or recovery guarantee. Constructors and rendering are
therefore deterministic and effect-free.

Framework behavior remains Ard-native. Views use internal checked casts because
Ard currently provides neither a generic `Component` bound nor safe direct
recursive generic substitution. Application code keeps concrete types and
ordinary values.

## Consequences

- Component composition is expressed entirely by returned views; nested lifetime
  bookkeeping is automatic.
- Stable identity preserves component and control state across updates and keyed
  moves, while committed removal resets both.
- The renderer is root-driven rather than fine-grained or dependency tracked.
- Lifecycle supports component-owned workers through scoped dispatch and a
  cancellation receiver, without a task runner or geometry hook.
- Primitive coverage remains intentionally narrower than imperative `cooper/ui`.
- Checked type errors and duplicate identity/ref violations are programmer errors.

## Related

- [Declarative framework guide](../declarative.md)
- [ADR 0002: Application API](./0002-define-application-api.md)
- [ADR 0015: Package entry points](./0015-define-package-entry-points-and-ui-namespace.md)
