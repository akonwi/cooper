# Cooper examples

These applications use the canonical persistent-Node API and currently require
`ard-dev` from Ard main (or Ard v0.38.0 once released).

## Input

`input.ard` runs one retained single-line Input.

```sh
ard-dev run input.ard
```

Type or paste to insert text, use Left/Right/Home/End and Backspace/Delete for
editing, click to place the cursor, and press Ctrl+C to exit.

## Form

`form.ard` composes three Inputs in a retained Box. Tab and Shift+Tab traverse
direct Node focus; mouse presses focus fields using cached target geometry.

```sh
ard-dev run form.ard
```

## Scrollable form

`scroll_form.ard` places eight retained Inputs inside ScrollView. It demonstrates
wheel fallback, translated mouse targeting, resize, and focused-descendant
reveal.

```sh
ard-dev run scroll_form.ard
```

## Attachment-scoped async work

`async.ard` starts background work from `Renderable.mount`. Detach or App
shutdown closes cancellation and suppresses stale dispatched mutation.

```sh
ard-dev run async.ard
```

## Filesystem explorer

`explorer.ard` asynchronously reads the current working directory into persistent
rows and responsive listing/detail panes. Tab focuses rows, Enter activates the
focused row, mouse presses activate direct hit targets, and the wheel scrolls
the listing.

```sh
ard-dev run explorer.ard
```

The loader snapshots inputs during mount and only creates/mutates retained Nodes
inside attachment-scoped UI dispatch.

## PTY smoke tests

```sh
ARD=ard-dev python3 test_input.py
ARD=ard-dev python3 test_form.py
ARD=ard-dev python3 test_scroll_form.py
ARD=ard-dev python3 test_async.py
ARD=ard-dev python3 test_explorer.py
```

The tests cover terminal startup/restoration, editing, focus, mouse input,
scrolling, resize, mount cancellation, asynchronous UI dispatch, filesystem
rows, and clean exit.
