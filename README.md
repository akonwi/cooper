# Cooper

**An Ard-native retained-mode TUI framework** powered by
[Vaxis](https://github.com/rockorager/vaxis).

Cooper keeps application state, hierarchy, layout geometry, focus, and event
targets in persistent Ard renderables. Layout updates attached Nodes in place,
and painting writes directly into one root cell buffer for Vaxis to diff.

## Status

Cooper is under active development and currently requires `ard-dev` from Ard
main (the promoted retained API depends on changes newer than v0.37.0; the
manifest targets the upcoming v0.38.0 release). The retained vertical slice
includes:

- persistent `Node` identity and explicit hierarchy mutation;
- row/column flex layout through Ard-native `Style`;
- retained `Box`, `Text`, `Input`, and `ScrollView` primitives;
- RGB cell styling and terminal attributes;
- direct capture/target/bubble event routing;
- direct focus identity, mouse hit testing, and focused-descendant reveal;
- attachment-scoped asynchronous dispatch and cancellation;
- deterministic headless tests and PTY-tested applications.

The earlier Surface-tree experiment has been removed. See
[the architecture](./docs/architecture.md) for the accepted clean-break design.

## Install

```sh
ard-dev add github.com/akonwi/cooper@latest
```

## Quick start

```ard
use cooper/app
use cooper/input
use cooper/style

fn main() {
  let application = app::new().expect("create Cooper app")
  let field = input::new(
    application.context(),
    placeholder: "Type here, then press Ctrl+C to quit",
    initial_style: style::new(
      width: style::percent(100.0),
      height: style::cells(1),
    ),
  )

  application.run(field).expect("run Cooper")
}
```

`Input` retains its value and cursor. It supports grapheme-aware editing,
Left/Right/Home/End, Backspace/Delete, paste, horizontal cursor visibility,
click focus, and mouse cursor placement. App owns Tab/Shift+Tab traversal and
Ctrl+C shutdown.

## Renderable model

Every renderable owns one persistent Node:

```ard
trait Renderable {
  fn node() mut Node
  fn mut mount(ctx: MountContext)
  fn paint(ctx: mut PaintContext)
  fn mut event(ctx: mut EventContext) EventResult
}
```

Constructors create detached renderables. Parent/child relationships change
through `add`, `remove`, reparenting, and `destroy`. Removal permits reuse;
reattachment receives a fresh mount scope; destruction recursively releases the
subtree.

`paint` observes retained state and writes directly into the root Ard cell
buffer. It does not rebuild a Surface or child description tree.

## Asynchronous effects

`mount` runs once for each structural attachment to a running root.
`MountContext` provides an attachment-scoped dispatch function and cancellation
receiver:

```ard
fn mut mount(ctx: node::MountContext) {
  async::start(fn() {
    select {
      ctx.cancellation.recv() => (),
      let result = load_data() => {
        let _ = ctx.dispatch(fn() {
          self.apply(result)
        })
      },
    }
  })
}
```

Detach or destroy closes cancellation, rejects future calls through the old
dispatch function, and suppresses queued stale actions. Reattachment creates a
new scope. Background work must only inspect or mutate retained state inside a
dispatched UI-thread closure.

See [`examples/async.ard`](./examples/async.ard).

## Layout and scrolling

`Box` is the configurable flex primitive. Public `Style` supports horizontal
and vertical direction, grow/shrink, alignment, gap, cell and percentage
lengths, display, position, and overflow. Tess/Yoga is currently an internal,
replaceable layout backend.

```ard
let content = box::new(ctx)
// Add persistent children.

let viewport = scroll::new(
  ctx,
  content,
  initial_style: style::new(
    width: style::percent(100.0),
    height: style::cells(1),
    grow: 1.0,
  ),
)
```

`ScrollView` retains requested and effective offsets separately, clips and
translates descendant geometry, bubbles wheel fallback, and reveals focused
Nodes after traversal or resize without snapping ordinary wheel movement back
to focus.

## Events and focus

Events target direct Node references and route capture → target → bubble.
`EventResult::handled` records handling without stopping traversal;
`ctx.stop_propagation()` stops it explicitly. Route attachment generations are
revalidated because capture handlers may mutate the tree.

Focus stores direct Node identity. Hit testing uses the same translated and
clipped screen geometry as painting and cursor placement.

## Examples

```sh
cd examples
ard-dev run input.ard
ard-dev run form.ard
ard-dev run scroll_form.ard
ard-dev run async.ard
ard-dev run explorer.ard
```

The explorer is an app-local asynchronous filesystem listing with responsive
listing/detail panes, keyboard activation, mouse targeting, resize handling,
and retained scrolling.

## Project structure

```text
app.ard          application runtime and Vaxis boundary
box.ard          generic retained flex container
cell_style.ard   backend-independent colors and attributes
context.ard      Node allocation, measurement, and cleanup ownership
event.ard        phased context, propagation, and dispatch result types
focus.ard        direct focus identity, traversal, and reveal
geometry.ard     rectangles and cached geometry
hit.ard          clipped direct-Node hit testing
input.ard        retained single-line Input
node.ard         Renderable, Node, hierarchy, mount, and destruction
paint.ard        root cell buffer and localized PaintContext
router.ard       capture/target/bubble delivery
runtime.ard      dispatch queue and cancellation scopes
scroll.ard       retained vertical ScrollView
style.ard        Ard-native layout vocabulary
text.ard         measured retained Text
ffi/             internal Tess/Yoga boundary
test/            deterministic headless tests
examples/        runnable PTY-tested applications
benchmarks/      retained layout and stress workloads
```

## Development

```sh
ard-dev test test

git diff --check

go test ./...

cd examples
ARD=ard-dev python3 test_input.py
ARD=ard-dev python3 test_form.py
ARD=ard-dev python3 test_scroll_form.py
ARD=ard-dev python3 test_async.py
ARD=ard-dev python3 test_explorer.py

cd ..
ARD=ard-dev python3 benchmarks/run.py
```

## Design principles

- Persistent Ard Nodes and renderable structs own framework and application
  state.
- Vaxis is a narrow terminal backend, not Cooper's public model.
- Tree mutation and retained state mutation are UI-thread-only.
- Layout, paint, hit testing, focus, and cursor placement share cached geometry.
- Paint the complete logical cell buffer first; optimize incrementally only in
  response to measurements.
- Prefer one configurable primitive and promote broader APIs only after repeated
  application-level usage.

## License

BSD 3-Clause. See [LICENSE](./LICENSE).
