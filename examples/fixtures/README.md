# PTY fixtures

These programs support focused regression tests and are not part of Cooper's
public example gallery:

- `scroll_form.ard` covers direct multi-child ScrollBox reveal, translated mouse
  targeting, wheel fallback, and resize.
- `async.ard` and `pre_run_destroy.ard` cover cancellation, dispatch, and
  destruction while work is pending.
- `lifecycle.ard` and `pre_start_signal.ard` cover nonblocking startup,
  suspend/resume, waiting, signals, and idempotent teardown.
- `interaction_lab.ard` is the end-to-end interaction contract fixture for ADR
  0003.
- `focus_without_mouse.ard` verifies terminal focus reporting independently of
  mouse mode.

The top-level `test_*.py` entrypoints build these fixtures into `ard-out/`.
