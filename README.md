# Cooper

**A retained mode TUI framework** for [Ard](https://ard.run), powered by
[Vaxis](https://github.com/rockorager/vaxis).

Cooper keeps application state directly in long-lived Ard widget structs.
Events mutate those widgets through `mut Widget`; rendering observes their
current state and returns composable cell surfaces.

## Status

Cooper is under active development. The current vertical slice provides a
direct Vaxis runtime, composable surfaces, Unicode text, retained single-line
inputs, weighted column layout, nested focus routing, mouse interaction,
retained vertical scrolling with focused-descendant reveal, and contextual
asynchronous UI dispatch.

See [the architecture](./docs/architecture.md) for the accepted design and
implementation milestones.

## Install

```sh
ard add github.com/akonwi/cooper@latest
```

## Quick start

```ard
use cooper
use cooper/input

fn main() {
  let field = mut input::new(
    value: "",
    placeholder: "Type here, then press Ctrl+C to quit",
  )

  cooper::run(mut field).expect("run Cooper")
}
```

`Input` retains its value and cursor directly. It supports Unicode grapheme
editing, Left/Right/Home/End movement, Backspace/Delete, horizontal scrolling,
paste, click focus, and grapheme-aware mouse cursor placement. The application
runtime owns Tab/Shift+Tab focus traversal and Ctrl+C shutdown.

See [`examples/form.ard`](./examples/form.ard) for nested focusable inputs,
[`examples/scroll_form.ard`](./examples/scroll_form.ard) for a wheel-scrollable
form, [`examples/async.ard`](./examples/async.ard) for mount-time background
work, and [`examples/explorer.ard`](./examples/explorer.ard) for an asynchronous
mouse-enabled Miller-column filesystem explorer.

## Widget model

Widgets render without mutating themselves and handle events through an
explicit mutable receiver contract:

```ard
trait Widget {
  fn render(ctx: RenderContext) Surface
  fn mut event(ctx: mut EventContext) EventResult
}
```

`EventContext` contains a terminal event, focused-target geometry, or a
mount/unmount lifecycle signal. Containers route or broadcast that context;
widgets opt into only the cases they need and may request relative focus paths.

The current runtime redraws the complete logical surface after state changes
and lets Vaxis efficiently diff terminal cells.

## Asynchronous updates

Every live `EventContext` exposes `dispatch` directly as a function field.
Background fibers perform slow work without touching widget state, then dispatch
a short retained-state mutation back to Cooper's UI loop. Accepted actions are
followed by a redraw; dispatch returns `stopped` after runtime shutdown. See the
async example for startup and cleanup handling.

## Filesystem explorer

The representative explorer example reads the current directory asynchronously,
opens selected directories in responsive detail panes, supports mouse and
keyboard navigation, and uses `/` to move focus into a retained search `Input`.
Run it with:

```sh
cd examples
ard run explorer.ard
```

## Scrolling

`ScrollView` retains a desired vertical offset, handles wheel events after its
routed child declines them, and reveals focused descendants after focus changes
or resize. Use tight flex when it should consume and clip to the remaining
bounded height:

```ard
let viewport = mut scroll::new(content, wheel_step: 2)
let page = mut layout::column(
  [
    layout::flex_item(heading),
    layout::flex_item(
      viewport,
      flex: 1,
      fit: layout::FlexFit::tight,
    ),
  ],
)
```

## Project structure

```text
cooper.ard      Widget contract and application runtime
event.ard       unified context, lifecycle, dispatch, and EventResult
focus.ard       rendered focus paths and traversal state
hit.ard         clipped routed Surface hit testing
runtime.ard     reentrant UI-dispatch queue
scroll.ard      retained vertical ScrollView
surface.ard     constraints, cells, surfaces, cursor, text measurement
text.ard        Unicode-aware stateless Text widget
input.ard       retained single-line Input widget
layout.ard      retained Column and weighted flex layout
test/           deterministic headless tests
examples/       runnable PTY-tested examples
```

## Development

```sh
ard test test

cd examples
python3 test_input.py
python3 test_form.py
python3 test_scroll_form.py
python3 test_async.py
python3 test_explorer.py
```

The PTY smoke tests cover terminal startup, editing, resize, nested keyboard
and mouse focus, cursor placement, wheel scrolling, async dispatch,
programmatic focus, filesystem navigation, redraws, and clean exit.

## Design principles

- Ard owns widget state, layout, event behavior, and surfaces.
- Vaxis is a narrow terminal backend rather than Cooper's public model.
- Rendering observes state; events mutate retained widgets.
- Layout uses signed `Int` dimensions and explicit unbounded constraints.
- A frame uses one terminal-aware text measurer for layout, cells, and cursor
  positions.
- Prefer deterministic headless tests and reserve PTYs for terminal integration.

## License

BSD 3-Clause. See [LICENSE](./LICENSE).
