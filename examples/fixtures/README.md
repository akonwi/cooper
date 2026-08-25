# PTY fixtures

These programs support focused regression tests and are not part of Cooper's
public example gallery:

- `clipboard.ard` covers OSC 52 write, clear, asynchronous read, concurrent-read
  rejection, suspend rejection/resume, response delivery, and App-lifetime
  cancellation.
- `scroll_form.ard` covers direct multi-child ScrollBox reveal, its built-in
  proportional scrollbar and terminal mouse drag, translated mouse targeting,
  wheel fallback, and resize.
- `horizontal_scroll.ard` covers two-axis ScrollBox state, both built-in bars,
  corner ownership, Shift+wheel, arrow keys, and horizontal terminal mouse drag.
- `select.ard` covers compact Select menu and TabSelect rendering, navigation,
  fast movement, activation callbacks, wheel/click input, indicator dragging,
  focus, overflow arrows, and resize.
- `async.ard` and `pre_run_destroy.ard` cover cancellation, dispatch, and
  destruction while work is pending.
- `lifecycle.ard` and `pre_start_signal.ard` cover nonblocking startup,
  suspend/resume, waiting, signals, and idempotent teardown.
- `interaction_lab.ard` is the end-to-end interaction contract fixture for ADR
  0003.
- `focus_without_mouse.ard` verifies terminal focus reporting independently of
  mouse mode.

The top-level `test_*.py` entrypoints build these fixtures into `ard-out/`.
