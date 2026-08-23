# Cooper examples

These applications exercise Cooper's accepted application API and require Ard
v0.38.0 or newer.

Every example uses `App.context`, the permanent `App.root`, persistent public
controls, and explicit focus policy. Most use blocking `run()`; the lifecycle
example demonstrates nonblocking startup.

## Quickstart

`quickstart.ard` recreates OpenTUI's imperative quickstart with nested styled
Boxes, inherited colors, mutable Text, application key listeners, and the
single-import `cooper/ui` control aliases.

```sh
ard run quickstart.ard
```

Use Left and Right to change the counter, or press Q to quit.

## Input

`input.ard` runs one retained single-line Input.

```sh
ard run input.ard
```

Type or paste to insert text, use Left/Right/Home/End and Backspace/Delete for
editing, or use readline-style bindings such as Ctrl+A/E/B/F, Ctrl+W/K/U,
and Alt+B/F/D. Click to place the cursor and press Ctrl+C to exit.

## Form

`form.ard` composes three Inputs in a Box. An App key listener implements Tab
and Shift+Tab traversal; mouse presses use Input's built-in autofocus.

```sh
ard run form.ard
```

## Scrollable form

`scroll_form.ard` adds labels and Inputs directly to a multi-child ScrollBox. It
demonstrates wheel fallback, translated mouse targeting, resize, and automatic
focused-child reveal.

```sh
ard run scroll_form.ard
```

## App-lifetime async work

`async.ard` waits in a background fiber, observes `Context.cancellation`, and
uses `Context.dispatch` to update a Text control on the UI thread. App teardown
cancels pending work and suppresses queued actions.

```sh
ard run async.ard
```

## Reusable application lifecycle

`lifecycle.ard` starts the event pump without blocking, waits independently,
and exercises idempotent startup, suspension, resume, repeated completion
waiting, and final destruction. It also verifies that the retained tree
survives terminal suspension.

```sh
ard run lifecycle.ard
```

## Filesystem explorer

`explorer.ard` asynchronously reads the current working directory and creates
persistent public Box and Text controls through UI dispatch. Tab focuses the
first row, Enter and mouse presses activate rows, and the listing ScrollBox
handles wheel input.

```sh
ard run explorer.ard
```

## Interaction Lab

`interaction_lab.ard` is the end-to-end acceptance program for ADRs 0003 and
0005. It combines nearest-ancestor focus, overlapping z-index controls,
captured and hit-routed drags, layout-driven hover, terminal focus, selectable
rich linked Unicode Text with double-click word selection, ellipsis overflow,
editable Input selection, and selection through a ScrollBox. Press M while the pointer is over
a hover tile to move another tile beneath the stationary pointer. Hover
`SELECTABLE` for a pointer cursor, then plain-click to open its link. OSC 8
metadata remains available for native
terminal previews and modifier-based activation.

```sh
ard run interaction_lab.ard
```

## PTY smoke tests

```sh
ARD=ard python3 test_input.py
ARD=ard python3 test_form.py
ARD=ard python3 test_scroll_form.py
ARD=ard python3 test_async.py
ARD=ard python3 test_lifecycle.py
ARD=ard python3 test_explorer.py
ARD=ard python3 test_interaction.py
```

The tests cover terminal startup/restoration, editing, explicit focus policy,
mouse input, scrolling, resize, App cancellation, asynchronous UI dispatch,
nonblocking startup, suspension/resume, filesystem rows, drag capture/drop
ordering, hover reconciliation, terminal focus, text and editable selection,
and clean exit.
