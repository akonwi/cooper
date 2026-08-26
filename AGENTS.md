# Cooper

An Ard-native imperative retained-mode TUI framework using
[Vaxis](https://github.com/rockorager/vaxis) as its terminal backend.

## Vision

See [`ADR 0002`](./docs/adrs/0002-define-application-api.md).

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

Public application modules stay at the package root and own their complete Ard
domain model and supporting logic. Keep only unsupported runtime mechanisms
with no public counterpart beneath `core/`: Node, paint, focus, hit testing,
routing, scheduling, and application runtime. Backend bindings stay beneath
`ffi/core/backend/`.

Import Vaxis as `vaxis`; do not alias it as `raw`.

## API principles

- Prefer one configurable primitive over many single-purpose variants.
- Expose each supported built-in control through `ui.ard` with direct constructor
  and type aliases.
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
  cancellation, Context ownership, clipboard lifetime, notification requests,
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

Current validation entry points:

```sh
ard test

cd examples
python3 test_layout_playground.py
python3 test_text_gallery.py
python3 test_dashboard.py
python3 test_stacking.py
python3 test_input_lab.py
python3 test_text_area.py
python3 test_event_inspector.py
python3 test_links.py
python3 test_terminal_focus.py
python3 test_widgets.py
python3 test_clipboard.py
python3 test_notification.py
python3 test_scroll_form.py
python3 test_horizontal_scroll.py
python3 test_select.py
python3 test_async.py
python3 test_lifecycle.py
python3 test_explorer.py
python3 test_interaction.py

cd ..
python3 benchmarks/run.py
```

## References

- Application API: [`ADR 0002`](./docs/adrs/0002-define-application-api.md)
- Terminal clipboard: [`ADR 0006`](./docs/adrs/0006-define-terminal-clipboard-access.md)
- Scrollbars and two-axis scrolling: [`ADR 0007`](./docs/adrs/0007-define-scrollbars-and-two-axis-scrolling.md)
- Select controls and Appearance overrides: [`ADR 0008`](./docs/adrs/0008-define-select-controls-and-appearance-overrides.md)
- Terminal-mediated notifications: [`ADR 0009`](./docs/adrs/0009-define-terminal-mediated-notifications.md)
- Terminal progress reporting: [`ADR 0010`](./docs/adrs/0010-define-terminal-progress-reporting.md)
- Vaxis source: `go.rockorager.dev/vaxis`
- Ard docs: https://ard.run
