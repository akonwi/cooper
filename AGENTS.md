# Cooper

An Ard-native retained-mode TUI framework using
[Vaxis](https://github.com/rockorager/vaxis) as its terminal backend.

## Architecture

The accepted direction is documented in
[`docs/architecture.md`](./docs/architecture.md). Read it before changing the
framework model.

Cooper is not a Vaxis binding. Ard owns widget state, layout, surfaces, event
results, focus state, and application helpers. Direct Go interop with Vaxis is
isolated to terminal-specific behavior.

## Widget contract

The framework depends on mutating trait receiver contracts:

```ard
trait Widget {
  fn render(ctx: RenderContext) Surface
  fn mut event(ctx: mut EventContext) EventResult
}
```

- Calling a mutating trait method requires a mutable receiver reference.
- A mutating implementation cannot satisfy a non-mutating contract.
- A non-mutating implementation may satisfy a mutating contract.
- `EventContext` carries one terminal event, focused-target geometry, or a
  mount/unmount lifecycle signal. It also exposes direct UI-thread dispatch and
  relative focus requests.
- Containers broadcast lifecycle signals and route terminal/focus contexts
  through exact retained child indexes. Leaves ignore context kinds they do not
  use.

Before adopting unfamiliar Ard syntax or interop behavior, use the
`ard-expert` sub-agent and verify the smallest shape with the current compiler.

## Architecture rules

### Ard owns framework behavior

Implement widgets, surfaces, layout, cell buffers, event results, focus state,
and application helpers in Ard. Call base Vaxis through direct Go interop. Add
a Go companion only after a concrete capability is proven inexpressible in Ard.

### Widgets retain state

Application state lives directly in long-lived Ard widget structs. Events
mutate those widgets through `mut Widget`. Do not introduce a separate generic
state registry or rebuild immutable widget descriptions after every event.

Rendering observes widget state and returns a `Surface`; it should not mutate
widget state. Start widget-owned asynchronous work from a mount lifecycle
context, not from rendering. Background work must call the context's `dispatch`
function before reading or mutating retained widget state.

### Surfaces are compositional

Widgets return sized, pure Ard surfaces containing cells, positioned child
surfaces, and optional cursor information. The runtime paints the completed
surface tree into Vaxis. Vaxis handles terminal-cell diffing.

Associate widget ownership with rendered children through routed positioned
surface edges. Do not require a widget implementation to upcast its own `self`
merely to construct a surface. Routed child indexes must identify one occurrence
per owner; ambiguous duplicate routes are not eligible for automatic focused
geometry resolution. The runtime derives focus order from the final unflattened
tree; containers route contexts through their retained child indexes.

### Layout is constraint-based

Parents derive child constraints, render children, and position the resulting
surfaces. Use VXFW as prior art, not as an API that must be wrapped.

Loose flex children preserve inherent height; `FlexFit::tight` children use
only their bounded allocation and may shrink. Use tight flex for viewports.

Use Ard `Int` for dimensions, coordinates, list indexes, and layout arithmetic.
Validate non-negative sizes at constructors and boundaries. Represent
unbounded constraints explicitly; do not use a maximum integer sentinel. Use
the frame's `RenderContext` measurer consistently for text layout, cells, and
cursor positions; the live runtime delegates to Vaxis's terminal-aware width.

### Keep the runtime simple

Initially redraw the complete logical surface after state changes and let Vaxis
diff terminal cells. Add incremental layout only in response to measured
performance problems.

Start event delivery at the root. Add focus paths and mouse hit testing from
the latest rendered surface tree when composition lands. Do not preemptively
copy the full capture/target/bubble system from `vaxis/ui`.

## Implementation milestones

1. Retained `Input` as the root widget: complete.
2. `Text`, `Column`, child surfaces, clipping, and two-pass flex allocation:
   complete.
3. Multiple inputs with focus routing and Tab/Shift+Tab traversal: complete.
4. Mouse hit testing, Input click focus, retained vertical scrolling,
   focused-descendant reveal, lifecycle contexts, and asynchronous UI-thread
   dispatch: complete.
5. A representative asynchronous filesystem explorer now exercises responsive
   horizontal composition, dynamic pane data, mouse input, and programmatic
   focus. Promote broader widget APIs only from demonstrated repetition.

## Module direction

```text
cooper.ard      public Widget contract and application runtime
surface.ard     Size, Point, Constraints, Cell, Surface
event.ard       unified event context, lifecycle, dispatch, and EventResult
focus.ard       focus path discovery and traversal state
hit.ard         clipped routed Surface hit testing
runtime.ard     reentrant UI-dispatch queue
scroll.ard      retained vertical ScrollView
text.ard        stateless Text widget
input.ard       retained Input widget
layout.ard      Column and flex layout
```

Module boundaries may change as later milestones expose better seams.

## API design principles

- Prefer one configurable function or widget over many single-purpose variants.
- Use Ard enums and structs in public APIs; convert Go-specific encodings at the
  backend boundary.
- Match upstream Vaxis terminal behavior unless a deliberate Cooper choice is
  documented.
- Keep direct Go imports narrow and terminal-specific operations separate from
  headless framework behavior.
- This project is not compatibility constrained yet. Prefer a clean API over
  aliases and deprecation layers.

## Verification

Run formatting and compiler validation on every changed Ard file.

Prefer deterministic headless tests for:

- event-driven widget mutation;
- surface cell snapshots;
- constraints, flex allocation, and clipping;
- focus order and hit paths.

Use PTY tests for terminal integration:

- startup and terminal restoration;
- keyboard input and resize events;
- cursor placement;
- clean quit.

Current validation entry points:

```sh
ard test test

cd examples
python3 test_input.py
python3 test_form.py
python3 test_scroll_form.py
python3 test_async.py
python3 test_explorer.py
```

## References

- Architecture: [`docs/architecture.md`](./docs/architecture.md)
- Vaxis source: `../vaxis` or `go.rockorager.dev/vaxis`
- VXFW prior art: `../vaxis/vxfw`
- Ard compiler source: `../ard`
- Ard docs: <https://ard.run>
