# Cooper architecture

Status: accepted.

## Goal

Cooper is an Ard-native retained-mode TUI framework with Vaxis as its terminal
backend. Application state lives in retained Ard widget structs. Cooper owns
terminal lifecycle, layout, rendering, event routing, focus, and redraws.

## Decisions

### Ard owns the framework

Widget types, layout, surfaces, event results, focus state, and application
helpers live in Ard. The framework calls base Vaxis directly through Ard's Go
interop.

A Go companion is added only for a capability that Ard cannot express. The MVP
must not introduce one preemptively.

### Widgets are retained Ard values

A widget is a long-lived Ard struct that owns its state:

```ard
trait Widget {
  fn mut init(ctx: InitContext)
  fn render(ctx: RenderContext) Surface
  fn mut event(ctx: mut EventContext) EventResult
}
```

`init` and `event` may mutate the retained widget and therefore require
`mut Widget` access. `render` observes state and produces a surface without
mutating widget state. Stateless implementations may satisfy mutating contracts
with non-mutating methods.

The runtime performs an unpainted discovery render and recovers opaque widget
owners. An owner absent from the current mount table receives a fresh mount
scope and `init` in root-first frontier order. The mount handle enters the table
only after infallible initialization returns. The runtime rerenders after each
frontier and repeats to a bounded fixed point, allowing parent initialization to
expose more widgets before painting.

After convergence, owners absent from the final tree are unmounted and removed
from the table. Reintroducing the same retained widget therefore creates a new
mount and calls `init` again. `InitContext.dispatch` is scoped to one mount:
unmount rejects future posts and suppresses accepted actions that have not yet
executed. Its cancellation receiver also closes so framework-started effects can
stop cooperatively. Constructor failures occur before a widget can become an
owner; `init` itself remains infallible.

Cooper has no widget `unmount` callback and cannot forcibly terminate arbitrary
fibers started outside its cancellation protocol. External resources and
non-cooperative work remain application concerns.

This depends on mutating trait receiver contracts added to Ard in
[ard#416](https://github.com/akonwi/ard/issues/416) and
[ard#417](https://github.com/akonwi/ard/pull/417).

### Rendering produces composable surfaces

Widgets do not draw directly into terminal windows. A widget returns a pure
Ard `Surface` containing:

- its measured cell size;
- its cell buffer;
- positioned child surfaces with optional retained-child route indexes;
- an optional opaque reference to the retained widget owner;
- optional cursor information;
- whether the current surface is a focus target.

The runtime paints the completed surface into the Vaxis root window. Vaxis
remains responsible for efficiently diffing terminal cells.

`surface.ard` cannot import the `Widget` trait without creating a module cycle,
so `Surface.owner` stores `Any?`. Parents attach retained mutable child
references when adding routed child surfaces, and the runtime recovers
`mut Widget` through `ard/unsafe`. A narrow `reflect` check rejects non-reference
owners before identity tracking. The root owner is attached at the runtime
boundary. This is a temporary type-erasure seam until Ard supports the cyclic
relationship directly.

Routed indexes continue to identify structural occurrences for focus and
geometry while decorative edges remain transparent. A routed index must
identify one child occurrence per owner and frame; ambiguous duplicate
occurrences are not eligible for automatic geometry resolution.

A focusable widget marks its root surface as focusable. `RenderContext` carries
an optional focus path relative to the current widget, so rendering can observe
whether the current occurrence is focused without mutating or duplicating
focus state in the widget. The runtime retains the authoritative path.

### Layout is constraint-based

`RenderContext` supplies minimum and maximum constraints. Widgets choose a
size within those constraints and return that size with their surface.
Containers render children with derived constraints, then position the
resulting surfaces.

The initial flex layout follows VXFW's two-pass shape:

1. measure children's inherent size on the main axis;
2. distribute remaining bounded space among flexible children;
3. render flexible children again with their allocated main-axis size;
4. position children sequentially and use the largest cross-axis extent.

Loose flex children preserve their inherent main-axis size and add their share
of remaining space. Tight flex children contribute no inherent main-axis size
under bounded layout and use only their allocated share, allowing viewports to
shrink while preserving the established non-shrinking default.

The Ard implementation uses `Int` for dimensions, coordinates, buffer indexes,
and layout arithmetic. Base Vaxis also uses `int`; signed arithmetic supports
clipping and scrolling and avoids unsigned underflow when content exceeds its
constraints. Public constructors enforce non-negative sizes.

Unbounded constraints must be explicit rather than encoded as a maximum
integer sentinel.

`RenderContext` also supplies terminal-aware text measurement. The live runtime
uses Vaxis's `RenderedWidth`; headless tests use a deterministic Unicode-width
fallback. Layout, cell spans, clipping, and cursor placement must use the same
measurer for a frame.

### Redraw the logical tree first

The MVP performs a full logical render after a handled state-changing event.
It does not implement dirty layout nodes or retained render objects. Terminal
performance still benefits from Vaxis's cell-buffer diffing.

Incremental layout is considered only after profiling demonstrates a need.

### Event routing grows from the rendered tree

The final unflattened surface tree is the authoritative frame snapshot. The
runtime collects focusable routed paths and opaque owner paths in depth-first
order and retains one optional current focus path. Tab and Shift+Tab move
through that order with wrapping.

For a focused or hit-tested occurrence, the runtime recovers each retained
owner and delivers directly in three phases: capture from root to the target
parent, target, then bubble back to root. Containers do not forward contexts to
children. `EventResult::handled` records that some owner handled the event but
does not stop traversal; explicit `ctx.stop_propagation()` does. This separation
allows ancestors to observe handled child updates and provides VXFW-style
fallback behavior such as scrolling only when a deeper target declined a wheel
event.

`RenderContext` carries the same relative path during rendering. An empty path
means the current widget is focused, a non-empty path identifies a focused
descendant, and no path means focus is outside the subtree. Initial or stale
focus is reconciled after rendering and triggers one corrective render before
painting. Focusability and route structure must not depend on focus state.

The runtime handles Tab, Shift+Tab, and Ctrl+C before focused delivery.
`EventContext.request_focus` lets a widget request a path relative to its
current routed owner; the runtime validates it against the next rendered tree.
Route paths currently identify retained child slots; dynamic keyed collections
will need stable occurrence keys to preserve semantic focus across reordering.

The runtime retains the final unflattened tree from the painted frame for mouse
hit testing. Hit testing follows ancestor clipping, visits later-painted
children first, and returns the deepest retained route with target-local cell
coordinates. A left press focuses the deepest focusable occurrence under the
point before delivering the localized mouse event. Decorative surfaces remain
part of their routed owner.

Hit results retain the size of each routed occurrence. Offscreen route
resolution additionally returns saturating global origins for one unambiguous
structural path. Focused `EventContext`s carry these route sizes and origins,
letting retained containers react using exact rendered geometry without
mutating state during rendering.

`ScrollView` renders one child with unbounded vertical space, positions it at a
negative retained offset, and relies on Surface clipping for its viewport.
Wheel events route to the deepest child first, then scroll the nearest ancestor
that can move. After focus changes, fallback, initial discovery, or resize, the
runtime routes current focused geometry; `ScrollView` privately adjusts its
offset and the runtime rerenders until nested viewports settle. A normal wheel
redraw does not reconcile focus geometry, so users may scroll away from the
focused widget. The requested offset is a desired position: rendering clamps it
to current bounds without discarding it, so temporarily shrunken content
restores the requested position if it grows again. Tight column flex supplies
adaptive bounded viewport height.

`EventContext.dispatch` is a function field for background-to-UI work. Before
each owner invocation, the runtime scopes it to that owner's current mount. The
live runtime backs scoped dispatch with an Ard-owned, mutex-protected action
queue and a coalesced wake channel selected beside Vaxis events. Posting is
nonblocking and reentrant; the UI loop executes bounded batches serially and
redraws afterward. Unmount rejects or suppresses stale scoped work; shutdown
stops and clears the base queue.
Background work may capture retained references but must only read or mutate
them inside dispatched closures. `InitContext` exposes a mount-scoped version of
the function plus a cancellation receiver. Effects must select or poll that
receiver cooperatively; arbitrary `async::start` fibers cannot be forcibly
terminated.

Cell coordinates are localized for each owner during phased mouse delivery.
Pixel coordinates remain terminal-relative until terminal cell-pixel geometry
is exposed.

## Runtime loop

The application runtime owns:

- the root `mut Widget`;
- the Vaxis instance and event stream;
- the latest rendered surface tree;
- focus state;
- redraw and quit requests;
- currently mounted owner identities and their cancellation scopes;
- the asynchronous update queue.

At a high level it:

1. opens Vaxis and creates the UI-dispatch queue;
2. performs an unpainted render and mounts newly discovered widget owners;
3. rerenders to a mount fixed point, unmounts absent owners, and paints the frame;
4. selects between terminal events and accepted UI actions;
5. derives an owner path and performs capture/target/bubble delivery, or executes
   dispatched state mutation;
6. reconciles mounts again whenever state requests a render;
7. cancels all mount scopes and stops dispatch;
8. restores the terminal.

Cleanup must remain explicit and reliable on both normal exit and errors.

## Module shape

The module boundaries may evolve, but Cooper separates these responsibilities:

```text
cooper.ard      public Widget contract and application runtime
surface.ard     Size, Point, Constraints, Cell, Surface
event.ard       phased context, dispatch, propagation, and EventResult
focus.ard       focus path discovery, reconciliation, and traversal
hit.ard         clipped hit testing, geometry, and opaque owner paths
runtime.ard     reentrant UI-dispatch queue and mount cancellation scopes
scroll.ard      retained vertical ScrollView
text.ard        stateless Text widget
input.ard       retained Input widget
layout.ard      Column and flex layout
```

## Verification strategy

Prefer headless tests for deterministic framework behavior:

- surface size and cell snapshots;
- layout allocation and clipping;
- event-driven widget mutation;
- focus traversal and hit paths.

Use PTY smoke tests for the integration boundary:

- startup and terminal restoration;
- keyboard input;
- resize handling;
- cursor placement;
- initialization-started asynchronous dispatch;
- programmatic focus and representative filesystem navigation;
- clean quit.

## Milestones

1. **Single input — complete:** a retained `Input` handles typing, backspace,
   cursor movement, redraw, and resize without a Go shim.
2. **Composition — complete:** `Text`, `Column`, positioned child surfaces, and
   weighted flex allocation.
3. **Focus — complete:** multiple inputs, nested route paths, keyboard routing,
   cursor ownership, and wrapped focus traversal.
4. **Interaction — complete:** routed mouse hit testing, click focus, Input
   cursor placement, retained vertical scrolling, focused-descendant reveal,
   opaque surface-owner event delivery, mount-scoped widget initialization and
   cancellation, and asynchronous UI dispatch.
5. **Library surface — in progress:** the asynchronous filesystem explorer
   exercises responsive horizontal composition, dynamic pane data, mouse
   selection, stale-safe loading, and programmatic focus. Promote reusable APIs
   only after repeated app-level shapes make them clear.

## Non-goals for the first milestone

- wrapping `vaxis/ui` or VXFW wholesale;
- a broad widget catalog;
- incremental render-tree reconciliation;
- graphics protocols or embedded terminals.
