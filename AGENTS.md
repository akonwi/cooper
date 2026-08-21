# Cooper

An Ard-native retained-mode TUI framework using
[Vaxis](https://github.com/rockorager/vaxis) as its terminal backend.

## Architecture

The accepted clean-break direction is documented in
[`docs/architecture.md`](./docs/architecture.md). Read it before changing the
framework model.

The persistent Node tree is the framework. The old `Widget.render() -> Surface`
runtime, discovery rendering, route indexes, and mount reconciliation are
superseded and are being removed rather than preserved for compatibility.

## Renderable contract

```ard
trait Renderable {
  fn node() mut Node
  fn mut mount(ctx: MountContext)
  fn paint(ctx: mut PaintContext)
  fn mut event(ctx: mut EventContext) EventResult
}
```

- Every renderable owns one persistent Node.
- A non-mutating implementation may satisfy a mutating contract.
- `paint` observes retained state and writes directly into the root cell buffer.
- `mount` runs once per structural attachment to a running root.
- Detach cancels attachment-scoped work; reattach receives a fresh scope.
- There is no general unmount callback.

Before adopting unfamiliar Ard syntax or interop behavior, use the
`ard-expert` sub-agent and verify the smallest shape with the current compiler.

## Architecture rules

### Persistent hierarchy is authoritative

Construct detached concrete renderables with application Context. Change the
tree only through `add`, `remove`, reparent, and `destroy`. Removal permits reuse;
destruction recursively releases resources and is permanent.

Application state lives directly in long-lived Ard renderable structs. Do not
introduce immutable widget-description rebuilding, owner discovery renders, or a
generic external state registry.

### Ard owns framework behavior

Implement Nodes, styles, cells, layout semantics, geometry, focus, events,
scrolling, and application helpers in Ard. Direct Go interop is limited to Vaxis
and the internal layout backend. Tess/Yoga must remain hidden behind Cooper's
validated Ard API and be replaceable by an Ard-native implementation.

### Paint directly

Layout mutates cached Node geometry. Paint traverses persistent Nodes in child
order into one Ard cell buffer. Vaxis only receives the completed cells and
handles terminal diffing. Do not reintroduce compositional Surface trees.

Use one frame-consistent text measurer for layout, grapheme spans, paint, and
cursor positions. Preserve wide-cell and style invariants when clipping or
overwriting.

### Events and focus use Node references

Derive capture/target/bubble paths, hit targets, and focus order from the
attached Node tree and cached geometry. Revalidate every owner before delivery
because handlers may mutate structure.

`EventResult::handled` records handling but does not stop propagation. Call
`ctx.stop_propagation()` explicitly. Wheel fallback depends on this distinction.

Focus stores direct Node identity. Scrolling translates cached descendant
geometry so paint, hit testing, cursor placement, and focus reveal agree.

### Effects are attachment-scoped

Tree mutation and retained state mutation are UI-thread-only. Background work
must use the current `MountContext.dispatch` and cooperatively observe
`MountContext.cancellation`.

Detach and destroy reject later scoped posts and suppress already queued stale
actions. Reattachment creates a fresh scope; old dispatch functions remain
stopped forever.

### Keep scheduling simple

Coalesce redraw requests, compute the attached layout, and repaint the complete
logical cell buffer. Let Vaxis diff terminal cells. Add incremental layout or
partial paint only in response to measured problems.

## Clean-break status

The retained cutover is complete: attachment scopes are active, modules use
canonical package paths, examples/tests use persistent Nodes, and the old
Surface runtime has been deleted. This project has no compatibility constraint.
Prefer deletion and a coherent API over aliases, adapters, or deprecation
layers.

## API principles

- Prefer one configurable primitive over many single-purpose variants.
- Primitive constructors are infallible; application/terminal creation may fail.
- Use Ard-native public structs and enums; convert backend values at boundaries.
- Keep application-specific loaders, searchable lists, and virtualization local
  until repetition demonstrates a stable reusable shape.
- Use Ard `Int` for geometry and indexes, and validate non-negative sizes at
  constructors and boundaries.

## Verification

Run formatting and compiler validation on every changed Ard file.

Prefer deterministic headless tests for:

- persistent identity and hierarchy mutation;
- attachment cancellation and stale dispatch suppression;
- layout, clipping, scrolling, and translated geometry;
- direct cell painting, styles, wide spans, and cursor placement;
- focus order, hit testing, and phased event routing;
- recursive destruction and Context ownership.

Use PTY tests for terminal startup/restoration, keyboard and mouse input,
scrolling, resize, cursor placement, asynchronous dispatch, explorer behavior,
and clean quit.

Current validation entry points:

```sh
ard-dev test test

cd examples
ARD=ard-dev python3 test_input.py
ARD=ard-dev python3 test_form.py
ARD=ard-dev python3 test_scroll_form.py
ARD=ard-dev python3 test_async.py
ARD=ard-dev python3 test_explorer.py

cd ..
ARD=ard-dev python3 benchmarks/run.py
```

## References

- Architecture: [`docs/architecture.md`](./docs/architecture.md)
- Vaxis source: `../vaxis` or `go.rockorager.dev/vaxis`
- Ard compiler source: `../ard`
- Ard docs: <https://ard.run>
