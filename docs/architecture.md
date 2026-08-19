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
- flattened positioned child layers as composition lands;
- optional cursor information.

The runtime paints the completed surface into the Vaxis root window. Vaxis
remains responsible for efficiently diffing terminal cells.

A surface does not need a widget to upcast its own `self`. Parents and the
runtime already hold children as `mut Widget`; framework composition helpers
associate those retained references with rendered surfaces for focus and event
routing.

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

The first vertical slice sends events directly to the root widget. Composition
then adds:

1. retained child references associated with child surfaces;
2. a focus path derived from the latest rendered tree;
3. keyboard delivery to the focused widget;
4. Tab and Shift+Tab traversal;
5. mouse hit testing from positioned and clipped surfaces.

Capture and bubble phases are deferred until a concrete widget requires them.
Asynchronous work returns to the UI thread through Vaxis synchronization.

## Runtime loop

The application runtime owns:

- the root `mut Widget`;
- the Vaxis instance and event stream;
- the latest rendered surface and child layers;
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
event.ard       EventContext and EventResult
text.ard        stateless Text widget
input.ard       retained Input widget
layout.ard      Column and flex layout
```

The natural recursive shape `Surface -> [PositionedSurface] -> Surface`
currently triggers an Ard AIR-lowering stack overflow tracked in
[ard#418](https://github.com/akonwi/ard/issues/418). Until it is fixed,
composition must flatten child surfaces into non-recursive layers before the
runtime paints them.

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
   cursor movement, redraw, resize, and Ctrl+C without a Go shim.
2. **Composition:** `Text`, `Column`, positioned child surfaces, and flex
   allocation.
3. **Focus:** multiple inputs, keyboard routing, cursor ownership, and focus
   traversal.
4. **Interaction:** mouse hit testing, scrolling, and asynchronous updates.
5. **Library surface:** refine naming and ergonomics only after the retained
   model has been exercised by a representative application.

## Non-goals for the first milestone

- wrapping `vaxis/ui` or VXFW wholesale;
- a broad widget catalog;
- capture/bubble event phases;
- incremental render-tree reconciliation;
- graphics protocols or embedded terminals.
