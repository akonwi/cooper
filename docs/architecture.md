# Cooper architecture

Status: accepted.

## Goal

Cooper is an Ard-native retained-mode TUI framework with Vaxis as its terminal
backend. Application state, renderable identity, hierarchy, layout geometry,
focus, and event targets persist between frames.

The earlier `Widget.render() -> Surface` experiment is superseded. Cooper is a
clean-break project with no compatibility requirement: the Surface tree,
discovery renders, route indexes, mount reconciliation, and rebuilt layout
model are removed rather than deprecated.

## Retained render tree

Every renderable owns one persistent `Node`. Parent/child relationships are
changed explicitly with `add`, `remove`, reparenting, and `destroy`.

```ard
trait Renderable {
  fn node() mut Node
  fn mut mount(ctx: MountContext)
  fn paint(ctx: mut PaintContext)
  fn mut event(ctx: mut EventContext) EventResult
}
```

A non-mutating implementation may satisfy a mutating contract. `paint` observes
retained state and writes cells; it must not mutate widget state.

`Node` owns framework state:

- parent and child references;
- the internal layout node and public Ard-native style;
- cached local and screen geometry;
- clipping and child translation used by scrolling;
- focusability, pointer participation, and focused state;
- attachment-scoped dispatch and cancellation;
- owner identity and destruction state.

Renderable structs own application state. Cooper does not introduce a separate
generic state registry and does not rebuild immutable widget descriptions after
events.

The framework mutates hierarchy only through Node methods. A retained identity
may occur once in the attached tree.

## Construction, attachment, and destruction

Construction is detached and fully initializes a concrete renderable. Primitive
constructors such as `box::new`, `text::new`, and `input::new` are infallible;
application and terminal creation may fail.

Attachment lifecycle is structural:

1. a detached renderable may be configured and assembled into a detached tree;
2. connecting a subtree to a running root mounts it root-first;
3. removing a subtree detaches it and cancels its attachment scopes, but permits
   reuse;
4. reattachment creates fresh scopes and invokes `mount` again;
5. `destroy` recursively cancels and permanently releases the subtree.

There is no general `unmount` callback. Attachment cancellation is the cleanup
signal for framework-scoped effects. External resources and non-cooperative
work remain application-owned.

The running root cannot be reparented or destroyed. App teardown first unmounts
the root, then stops dispatch, destroys the Context-owned nodes, and restores
the terminal.

## Attachment-scoped effects

`MountContext` exposes:

```ard
struct MountContext {
  dispatch: fn(fn()) Void!DispatchError
  cancellation: Receiver<Void>
}
```

Each attached Node receives a fresh scope. Detach and destroy:

- close the cancellation receiver;
- reject later calls through the old dispatch function;
- suppress accepted actions that remain queued.

Reattachment never reopens an old scope. It creates a new scope and a new
dispatch capability. Background work must cooperatively observe cancellation
and may only read or mutate retained state inside a dispatched UI-thread
closure.

A renderable that starts no effects implements a no-op `mount`.

## Direct layout and painting

The hierarchy is also the layout tree. Parents do not render child descriptions
or allocate child Surfaces. The internal layout backend computes attached Node
geometry in place.

Painting traverses persistent Nodes in child order and writes directly into one
root Ard cell buffer. Each owner receives a clipped `PaintContext` localized to
its cached screen bounds. Scrolling translates descendant screen geometry, so
painting, hardware cursor placement, focus reveal, and hit testing share the
same coordinates.

The cell model is backend-independent. It supports RGB foreground/background
and bold, dim, italic, underline, blink, reverse, and strike attributes. The
Vaxis boundary converts cells immediately before terminal rendering. Vaxis
remains responsible for terminal-cell diffing.

The MVP performs a complete layout and logical-buffer paint for a requested
frame. Redraw requests are coalesced. Incremental layout and partial paint are
added only after profiling demonstrates a need.

## Layout API and backend

Public layout vocabulary is Ard-native:

- `Style`;
- row and column flex direction;
- grow and shrink;
- alignment and justification;
- cell, percentage, intrinsic, and stretch lengths;
- padding, margin, gap, display, position, and overflow.

Dimensions, coordinates, and indexes use Ard `Int`. Constructors and backend
boundaries reject negative sizes. Text measurement for layout and paint uses one
frame-consistent measurer; the live runtime delegates to Vaxis.

Tess/Yoga is the initial internal backend. Its types and fallible primitive API
do not escape Cooper. Cooper owns Node lifetime and frees every backend node
explicitly. An Ard-native Yoga implementation may replace Tess later without
changing the public tree, event, or paint contracts. Backend replacement is not
a prerequisite for accepting the retained architecture.

Scroll content is non-shrinking on the scroll axis. A ScrollView keeps requested
and effective offsets separately, clips descendants, supports nested wheel
fallback, and reveals focused descendant identities without snapping ordinary
wheel movement back to focus.

## Events, hit testing, and focus

The latest attached Node tree and cached geometry are authoritative.

Terminal events route through direct Node references in three phases:

1. capture from root to target parent;
2. target;
3. bubble from target parent to root.

`EventResult::handled` records handling but does not stop propagation. Owners
call `ctx.stop_propagation()` explicitly. This permits ancestor fallback, such
as a ScrollView consuming a wheel event only when a deeper target did not.

A route snapshot is revalidated before each invocation. Structural mutation
during capture can detach or destroy later owners without stale delivery.
Event dispatch is scoped to the current owner's attachment.

Hit testing follows ancestor clipping, visits later-painted children first, and
returns the deepest pointer-enabled Node plus target-local coordinates. Focus
stores a direct Node reference and traverses visible focusable Nodes in stable
preorder with wrapping. Detach reconciles by prior ordinal. Initial focus,
programmatic focus, fallback, resize, and layout changes reveal focused
descendants through nested ScrollViews.

Tab, Shift+Tab, and Ctrl+C are App policies applied only to key press/repeat
rather than paste or release events.

## Application runtime

The intended application shape is:

```ard
let application = try app::new()
let ctx = application.context()
let root = box::new(ctx)
// Build the persistent tree.
try application.run(root)
```

The App owns:

- Vaxis and terminal restoration;
- the running root;
- the Context and all allocated Nodes;
- focus state;
- the queue-backed UI dispatch function;
- coalesced redraw wakeups;
- layout, paint, cursor, and event routing.

Tree and widget mutation is UI-thread-only. Background work posts short actions
to App dispatch. Before geometry-dependent input, pending redraw work is laid
out and painted so hit testing never uses an intentionally stale frame.

## Ownership and unsafe seam

A Node stores its concrete owner as `Any` because Ard cannot yet directly model
the cyclic `Node`/`Renderable` relationship. Binding validates and recovers
`mut Renderable` through one narrow `ard/unsafe` seam. Public behavior and tree
identity remain Ard-owned; Go interop is isolated to terminal and internal
layout operations.

Context tracks every allocated Node and guarantees terminal-first, recursive
cleanup. Measured descendants are freed individually; backend recursive-free
helpers are not used.

## Canonical module direction

```text
app.ard             application runtime and Vaxis boundary
box.ard             generic retained flex container
cell_style.ard      backend-independent colors and attributes
context.ard         Node allocation, measurement, and cleanup ownership
event.ard           phased event context and attachment-scoped dispatch
focus.ard           direct focus identity, traversal, and reveal
geometry.ard        points, rectangles, and cached geometry
hit.ard             clipped direct-Node hit testing
input.ard           retained single-line Input
node.ard            Renderable, Node, hierarchy, mount, and destruction
paint.ard           root cell buffer and localized PaintContext
router.ard          capture/target/bubble delivery
runtime.ard         dispatch queue and cancellation scopes
scroll.ard          retained vertical ScrollView
style.ard           Ard-native layout vocabulary
text.ard            measured retained Text
```

App-specific searchable lists, filesystem loaders, and virtualization remain in
applications or benchmarks until repeated usage demonstrates a stable public
shape.

## Verification and cutover

The retained runtime replaces the old implementation in one clean break:

1. settle and test attachment-scoped mount cancellation;
2. promote retained modules to canonical paths;
3. rewrite all examples and tests against persistent Nodes;
4. remove Surface, discovery rendering, route indexes, and the old runtime;
5. update public documentation and run the complete retained validation matrix.

Required headless coverage includes hierarchy identity, layout, clipping, cell
styles, cursor behavior, focus, hit testing, phased routing, structural mutation
during events, attach/detach/reattach cancellation, stale dispatch suppression,
scrolling, recursive destruction, and context ownership.

PTY coverage includes startup/restoration, input, focus traversal, mouse input,
scrolling, resize, asynchronous dispatched updates, the filesystem explorer,
and clean quit.

Performance gates use repeatable process-level benchmarks for 1,000-node layout,
single-node updates, responsive resize, repeated attachment mutation, deep
clipping/hit traversal, and a 10,000-row virtualized workload. Benchmarks guide
optimization but do not expose Tess or virtualization as public API.
