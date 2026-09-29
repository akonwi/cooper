# Cooper

An Ard-native imperative retained-mode TUI framework using
[Vaxis](https://github.com/rockorager/vaxis) as its terminal backend.

## Vision

- Before adopting unfamiliar Ard syntax or interop behavior, use the `ard-expert`
sub-agent and verify the smallest shape with the current compiler.

## Ard owns framework behavior

Implement Nodes, styles, colors, cells, layout semantics, geometry, focus,
events, listeners, scrolling, controls, and application helpers in Ard. Direct
Go interop is limited to Vaxis, the internal layout backend, and isolated
platform services that Ard does not expose, such as opening a URL with the
system handler. Tess/Yoga types
and fallible setters must remain hidden behind Cooper's validated API and remain
replaceable by an Ard-native implementation.

`cooper.ard` is the canonical application entry point and owns App plus the
`app(...)` constructor. `ui.ard` is the canonical view-construction facade over
focused implementation modules beneath `ui/`; it exposes controls, layout,
colors, geometry, selection, and rich-text values. Neither facade may be
imported by lower implementation modules. Application-scoped capability modules
such as Runtime, animation, clipboard, events, notifications, terminal progress,
and testing remain at the package root. App owns one Runtime lifetime, exposes
that Runtime as `application.context`, and binds its Root to the same identity.
Cooper has no separate application Context type. Keep only unsupported runtime
mechanisms with no public counterpart beneath `core/`: Node, paint, focus, hit
testing, routing, and scheduling. Backend bindings stay beneath
`ffi/`, with one directory per Go package and no additional category nesting.

Import Vaxis as `vaxis`; do not alias it as `raw`.

## API principles

- Prefer one configurable primitive over many single-purpose variants.
- Expose each supported built-in control and common view value through `ui.ard`
  with direct constructor, helper, and type aliases.
- Primitive constructors are infallible; application/terminal creation may fail.
- Use Ard-native public structs and enums and convert backend values at
  boundaries.
- Use Ard `Int` for geometry and indexes and validate non-negative sizes.
- Style is open value data validated when applied.
- Expected conditional outcomes use Bool; recoverable runtime failures use
  Result; programmer contract violations panic.
- Cleanup and listener removal functions are idempotent.
- Keep app-specific loaders, searchable lists, and virtualization local until
  repetition demonstrates a stable reusable shape.

## Verification

Run formatting and compiler validation on every changed Ard file.

Prefer deterministic headless tests for:

- App/Root startup, waiting, suspend/resume, destruction, dispatch,
  cancellation, Runtime ownership, clipboard lifetime, notification requests,
  and terminal progress cleanup;
- persistent identity, indexed reorder/reparent, detach, and destruction;
- layout, clipping, two-axis scrolling, scrollbar interaction, wrapping, and
  translated geometry;
- direct cells, text styles, wide spans, and cursor placement;
- listener order, event prevention, bubbling, and structural mutation;
- explicit focus, no-fallback behavior, hit testing, and reveal;
- Input editing/commit callbacks and nested ScrollBox fallback.

Use PTY tests for terminal startup/restoration, raw keyboard/mouse/paste input,
resize, cursor placement, asynchronous dispatch, examples, and clean quit.

Validation entry points:

```sh
ard test          # headless unit and integration tests
go test ./...     # Go bridge tests
```

PTY tests live in `examples/test_*.py`. Run the one relevant to your change,
or the example's own test if it has one. Benchmarks: `python3 benchmarks/run.py`.

## Module structure

```text
cooper.ard       canonical App, Runtime, Root, and event entry point
ui.ard           canonical controls, layout, color, geometry, and text facade
ui/              focused UI implementation modules
  box.ard
  color.ard
  editor.ard     shared editable-text engine
  geometry.ard
  image.ard
  input.ard
  scroll_box.ard
  scrollbar.ard
  select.ard
  selection.ard
  style.ard
  text.ard
  text_area.ard
  text_area_layout.ard
animation.ard    Runtime-owned timelines and springs, easing, and interpolation
clipboard.ard    Runtime-exposed OSC 52 clipboard service
cui.ard          declarative component layer (experimental)
event.ard        Cooper-owned events, controls, and propagation state
keymap.ard       typed commands, scoped bindings, and shortcut discovery
notification.ard accepted notification request snapshots
root.ard         permanent Runtime-bound Root
runtime.ard      application capabilities, retained ownership, lifecycle, and backend state
screen.ard       terminal screen mode configuration
terminal_progress.ard terminal progress state and report values
testing.ard      headless TestApp, frame snapshots, and terminal title history
core/            unsupported runtime mechanisms
  event_delivery.ard
  focus.ard
  graphics.ard
  hit.ard
  keymaps.ard
  layout.ard
  node.ard
  paint.ard
  pointer.ard
  router.ard
  runtime.ard
  selection_state.ard
  terminal_events.ard
  virtual_extent.ard
ffi/             isolated Go bridges, one directory per package
  contextbridge/ adapts Go context/cancel return pairs
  numberbridge/  numeric conversions missing from Ard
  vaxisbridge/   Vaxis modifier-bit testing
  signalwatch/   OS signal subscriptions and terminal-size queries
  urlopen/       platform URL handlers
test/            deterministic integration tests
examples/        curated runnable applications and PTY tests
  fixtures/      focused non-gallery regression programs
benchmarks/      retained layout and stress workloads
```

## Design principles

- Persistent Ard Nodes and concrete controls own framework and application
  state.
- Vaxis is a narrow terminal backend, not Cooper's public model.
- Tree and retained-state mutation are UI-thread-only.
- Layout, drawing, hit testing, focus, and cursor placement share cached
  geometry.
- Paint the complete logical buffer first; optimize only after measurement.
- Prefer one configurable primitive and promote broader APIs only after repeated
  application use.

## References

- Architecture decisions: [`docs/adrs/`](./docs/adrs/) (see [`docs/README.md`](./docs/README.md) for the index)
- Vaxis source: `github.com/akonwi/vaxis` (Cooper distribution fork)
- Ard docs: https://ard.run
