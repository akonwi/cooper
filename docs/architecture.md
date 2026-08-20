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
  fn render(ctx: RenderContext) Surface
  fn mut event(ctx: mut EventContext, event: vaxis::Event) EventResult
}
```

`render` observes state and produces a surface. It does not mutate widget
state. `event` may mutate the retained widget and therefore requires
`mut Widget` access. Stateless implementations may satisfy the mutating
contract with a non-mutating method.

This depends on mutating trait receiver contracts added to Ard in
[ard#416](https://github.com/akonwi/ard/issues/416) and
[ard#417](https://github.com/akonwi/ard/pull/417).

### Rendering produces composable surfaces

Widgets do not draw directly into terminal windows. A widget returns a pure
Ard `Surface` containing:

- its measured cell size;
- its cell buffer;
- positioned child surfaces with optional retained-child route indexes;
- optional cursor information;
- whether the current surface is a focus target.

The runtime paints the completed surface into the Vaxis root window. Vaxis
remains responsible for efficiently diffing terminal cells.

A surface does not need a widget to upcast its own `self`. Parents associate
positioned child surfaces with indexes in their retained child lists. These
routed edges form structural widget paths for focus and event delivery while
decorative surface edges remain transparent.

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
runtime collects focusable routed paths in depth-first order and retains one
optional current path. Tab and Shift+Tab move through that order with wrapping.
A routed `EventContext` starts at the root; each retained container consumes
one path segment and delivers the event to exactly one child. It never probes
siblings for the first handler.

`RenderContext` carries the same relative path during rendering. An empty path
means the current widget is focused, a non-empty path identifies a focused
descendant, and no path means focus is outside the subtree. Initial or stale
focus is reconciled after rendering and triggers one corrective render before
painting. Focusability and route structure must not depend on focus state.

The runtime handles Tab, Shift+Tab, and Ctrl+C before focused delivery. Route
paths currently identify retained child slots; dynamic keyed collections will
need stable occurrence keys to preserve semantic focus across reordering.

The runtime retains the final unflattened tree from the painted frame for mouse
hit testing. Hit testing follows ancestor clipping, visits later-painted
children first, and returns the deepest retained route with target-local cell
coordinates. A left press focuses the deepest focusable occurrence under the
point before delivering the localized mouse event. Decorative surfaces remain
part of their routed owner.

Capture and bubble phases are deferred until a concrete widget requires them.
Pixel coordinates remain terminal-relative when cell coordinates are localized
until terminal cell-pixel geometry is exposed. Asynchronous work returns to the
UI thread through Vaxis synchronization.

## Runtime loop

The application runtime owns:

- the root `mut Widget`;
- the Vaxis instance and event stream;
- the latest rendered surface tree;
- focus state;
- redraw and quit requests.

At a high level it:

1. opens Vaxis;
2. renders the root under current terminal constraints;
3. paints the surface and calls `Render`;
4. waits for an event;
5. routes the event to the retained widget tree;
6. renders again when requested;
7. restores the terminal on exit.

Cleanup must remain explicit and reliable on both normal exit and errors.

## Module shape

The module boundaries may evolve, but Cooper separates these responsibilities:

```text
cooper.ard      public Widget contract and application runtime
surface.ard     Size, Point, Constraints, Cell, Surface
event.ard       EventContext, routes, and EventResult
focus.ard       focus path discovery, reconciliation, and traversal
hit.ard         clipped routed Surface hit testing
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
- clean quit.

## Milestones

1. **Single input — complete:** a retained `Input` handles typing, backspace,
   cursor movement, redraw, and resize without a Go shim.
2. **Composition — complete:** `Text`, `Column`, positioned child surfaces, and
   weighted flex allocation.
3. **Focus — complete:** multiple inputs, nested route paths, keyboard routing,
   cursor ownership, and wrapped focus traversal.
4. **Interaction — in progress:** routed mouse hit testing, click focus, and
   Input cursor placement are complete; scrolling and asynchronous updates
   remain.
5. **Library surface:** refine naming and ergonomics only after the retained
   model has been exercised by a representative application.

## Non-goals for the first milestone

- wrapping `vaxis/ui` or VXFW wholesale;
- a broad widget catalog;
- capture/bubble event phases;
- incremental render-tree reconciliation;
- graphics protocols or embedded terminals.
