# Cooper

**A retained mode TUI framework** for [Ard](https://ard.run), powered by
[Vaxis](https://github.com/rockorager/vaxis).

Cooper keeps application state directly in long-lived Ard widget structs.
Events mutate those widgets through `mut Widget`; rendering observes their
current state and returns composable cell surfaces.

## Status

Cooper is under active development. The current vertical slice provides a
direct Vaxis runtime, composable surfaces, Unicode text, retained single-line
inputs, weighted column layout, nested focus routing, and mouse interaction.

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

See [`examples/form.ard`](./examples/form.ard) for nested columns with multiple
focusable inputs.

## Widget model

Widgets render without mutating themselves and handle events through an
explicit mutable receiver contract:

```ard
trait Widget {
  fn render(ctx: RenderContext) Surface
  fn mut event(ctx: mut EventContext, event: vaxis::Event) EventResult
}
```

The current runtime redraws the complete logical surface after state changes
and lets Vaxis efficiently diff terminal cells.

## Project structure

```text
cooper.ard      Widget contract and application runtime
event.ard       EventContext, event routes, and EventResult
focus.ard       rendered focus paths and traversal state
hit.ard         clipped routed Surface hit testing
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
```

The PTY smoke tests cover terminal startup, editing, resize, nested keyboard
and mouse focus, cursor placement and redraws, and clean exit.

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
