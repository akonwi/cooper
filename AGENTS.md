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
  fn mut init(ctx: InitContext)
  fn render(ctx: RenderContext) Surface
  fn mut event(ctx: mut EventContext) EventResult
}
```

- Calling a mutating trait method requires a mutable receiver reference.
- `init` runs once per mount, immediately after an owner first appears in an
  unpainted discovery tree. It may mutate state and start mount-scoped effects.
- A mutating implementation cannot satisfy a non-mutating contract.
- A non-mutating implementation may satisfy a mutating contract.
- `EventContext` carries one terminal event or focused-target geometry. It also
  exposes capture/target/bubble phase, mount-scoped UI-thread dispatch,
  propagation control, and relative focus requests.
- Routed surfaces retain opaque `Any` references to their widget owners. The
  runtime recovers `mut Widget` references and invokes each owner directly;
  containers do not forward events.

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
widget state. The runtime performs an unpainted discovery render, directly calls
`init` on owners that are not currently mounted, then rerenders before painting.
Repeat discovery after every state-driven render mounts dynamically introduced
widgets. Owners absent from the converged tree are unmounted; their
`InitContext` cancellation signal closes, later dispatch is rejected, and
already queued scoped actions are suppressed. Reintroducing the same retained
widget creates a fresh mount and calls `init` again. Background work must
cooperatively observe cancellation and dispatch before reading or mutating
retained widget state. There is no widget `unmount` callback; cleanup outside
framework-scoped effects remains application-owned.

### Surfaces are compositional

Widgets return sized, pure Ard surfaces containing cells, positioned child
surfaces, and optional cursor information. The runtime paints the completed
surface tree into Vaxis. Vaxis handles terminal-cell diffing.

Associate widget ownership with rendered children through routed positioned
surface edges. Each routed child surface stores its retained owner opaquely as
`Any`, avoiding the `surface` → `cooper` module cycle. Parents attach their child
references after rendering; the runtime recovers them as `mut Widget` through
`ard/unsafe` and uses a narrow `reflect` check to reject non-reference owners.
Routed child indexes still identify occurrences for focus and
geometry. Ambiguous duplicate routes are not eligible for automatic geometry
resolution.

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

Derive event owner paths, focus paths, and mouse hit targets from the latest
rendered surface tree. Deliver directly through the owner path in
capture/target/bubble order. `EventResult::handled` records handling but does not
stop propagation; widgets explicitly call `ctx.stop_propagation()` when needed.

## Implementation milestones

1. Retained `Input` as the root widget: complete.
2. `Text`, `Column`, child surfaces, clipping, and two-pass flex allocation:
   complete.
3. Multiple inputs with focus routing and Tab/Shift+Tab traversal: complete.
4. Mouse hit testing, Input click focus, retained vertical scrolling,
   focused-descendant reveal, direct surface-owner event delivery, mount-scoped
   widget initialization/cancellation, and asynchronous UI-thread dispatch:
   complete.
5. A representative asynchronous filesystem explorer now exercises responsive
   horizontal composition, dynamic pane data, mouse input, and programmatic
   focus. Promote broader widget APIs only from demonstrated repetition.

## Module direction

```text
cooper.ard      public Widget contract and application runtime
surface.ard     Size, Point, Constraints, Cell, Surface
event.ard       phased event context, dispatch, and EventResult
focus.ard       focus path discovery and traversal state
hit.ard         clipped routed Surface hit testing and owner paths
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
