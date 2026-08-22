# Cooper

**An Ard-native imperative retained-mode TUI framework** powered by
[Vaxis](https://github.com/rockorager/vaxis).

Cooper keeps application state, control identity, hierarchy, layout geometry,
focus, listeners, and event targets in persistent Ard controls. Layout updates
attached Nodes in place, and drawing writes directly into one logical cell
buffer for Vaxis to diff.

## Status

Cooper is under active development and currently requires `ard-dev` from Ard
main. The accepted application API is now being implemented, and the runnable
examples will be migrated during that work.

The canonical design is the accepted
[application API ADR](./docs/adrs/0002-define-application-api.md). Cooper has no
compatibility constraint while it is implemented.

## Accepted application shape

> This is the accepted target API. It will become runnable as the implementation
> cutover proceeds.

```ard
use cooper/app
use cooper/input
use cooper/style

fn main() {
  let application = app::new().expect("create Cooper app")
  let field = input::new(
    application.context,
    placeholder: "Type here, then press Ctrl+C to quit",
    style: style::new(
      width: style::percent(100.0),
      height: style::cells(1),
    ),
  )

  application.root.add(field)
  field.focus()
  application.run().expect("run Cooper")
}
```

App exposes its constructor Context and permanent terminal-sized Root. Controls
are persistent references: construct them once, add them to the tree, and
mutate them through setters. `run()` is blocking and one-shot; App guarantees
terminal teardown.

## Retained model

Every built-in control owns one persistent internal Node. Parent/child
relationships change through indexed `add`, `remove`, reparenting, `destroy`,
and `destroy_recursively`.

- Removal detaches without destroying.
- Same-parent reorder preserves attachment.
- Cross-parent reparent receives a fresh attachment scope.
- `destroy` destroys one control and preserves detached children.
- `destroy_recursively` destroys the complete subtree.
- App teardown destroys all remaining Context-owned controls.

The internal Renderable protocol is language-visible beneath `core/` but is not
yet a supported custom-control API.

## Runtime behavior

- Context dispatch queues application work on the UI thread and exposes
  App-lifetime cancellation.
- Frame requests are demand-driven and coalesced.
- Layout and drawing use one frame-consistent grapheme/terminal-width measurer.
- Drawing writes directly into one backend-independent cell buffer.
- Vaxis input is converted to Cooper-owned event values.
- Keyboard and paste run through App listeners and then the focused control.
- Mouse input targets the deepest hit control and bubbles through ancestors.
- Focus is explicit or caused by configurable mouse autofocus; Cooper does not
  reserve Tab or choose fallback focus.

## Initial controls

- `Box` — indexed flex container with background, border, and title;
- `Text` — multiline plain text with terminal-aware wrapping and TextStyle;
- `Input` — grapheme-aware single-line editing, validation, and callbacks;
- `ScrollBox` — focusable multi-child vertical scrolling container.

Public layout uses Ard-native Style, Color, Rect, and Geometry values.
Tess/Yoga remains a hidden and replaceable internal layout backend.

## Installation

```sh
ard-dev add github.com/akonwi/cooper@latest
```

Published revisions may lag the accepted target API while the clean-break
implementation is underway.

## Examples

Current runnable examples exercise the retained implementation baseline and
will be migrated during the application API cutover:

```sh
cd examples
ard-dev run input.ard
ard-dev run form.ard
ard-dev run scroll_form.ard
ard-dev run async.ard
ard-dev run explorer.ard
```

See [`examples/README.md`](./examples/README.md) for current behavior and
migration status.

## Target module structure

```text
app.ard          App facade and Vaxis boundary
box.ard          configurable retained flex container
color.ard        backend-independent RGB color
context.ard      public construction, dispatch, and cancellation capability
event.ard        Cooper-owned input events and listener controls
geometry.ard     Rect and cached Geometry
input.ard        retained single-line Input
root.ard         permanent terminal-sized Root
scroll_box.ard   retained vertical ScrollBox
style.ard        Ard-native layout vocabulary
testing.ard      headless TestApp and frame snapshots
text.ard         Text and TextStyle
core/            unsupported runtime, layout, and backend implementation
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

- Persistent Ard Nodes and concrete controls own framework and application
  state.
- Vaxis is a narrow terminal backend, not Cooper's public model.
- Tree and retained-state mutation are UI-thread-only.
- Layout, drawing, hit testing, focus, and cursor placement share cached
  geometry.
- Paint the complete logical buffer first; optimize only after measurement.
- Prefer one configurable primitive and promote broader APIs only after repeated
  application use.

## License

BSD 3-Clause. See [LICENSE](./LICENSE).
