# 0010: Define Terminal Progress Reporting

## Status

Accepted

## Context

Ghostty renders OSC 9;4 progress reports as terminal-surface progress, including
an animated indeterminate bar. Kit uses the indeterminate and remove forms to
show when an agent turn is active. The same protocol also defines normal,
error, and paused states with optional percentages.

This is terminal chrome rather than a retained Cooper control or desktop
notification. It belongs on Context because Context is passed to background work
and already owns terminal-mediated side effects. A progress report persists in
the terminal until replaced or removed, so Cooper must coordinate it with App
suspension and destruction to avoid stale progress after terminal ownership is
released.

Vaxis does not expose a dedicated progress-reporting method, but its
`Vaxis.Notify("", body)` emits `OSC 9;<body> ST`. Cooper can therefore emit fixed,
validated `4;...` numeric payloads through Vaxis without writing directly to the
terminal or accepting arbitrary control text.

## Decision

### Context API

Add an Ard-native state enum and report value:

```ard
enum State {
  remove,
  normal,
  error,
  indeterminate,
  paused,
}

struct Report {
  state: State,
  percent: Int?,
}
```

Applications update terminal progress through Context:

```ard
use cooper/terminal_progress

let _ = application.context.progress(
  terminal_progress::State::indeterminate,
)

let _ = application.context.progress(
  terminal_progress::State::normal,
  percent: 42,
)

defer application.context.progress(
  terminal_progress::State::remove,
)
```

```ard
impl Context {
  fn mut progress(
    state: terminal_progress::State,
    percent: Int?,
  ) Bool
}
```

The method returns true when Cooper selected and invoked a terminal progress
backend. It returns false when unsupported, suspended, stopping, or destroyed.
It does not request a Cooper frame.

Percentages must be between 0 and 100. `normal` requires a percentage;
`remove` and `indeterminate` reject one. `error` and `paused` accept an optional
percentage. Invalid combinations are programmer contract violations and panic.

States map to OSC 9;4 as follows:

| State | Sequence payload |
| --- | --- |
| `remove` | `4;0` |
| `normal` | `4;1;<percent>` |
| `error` | `4;2` or `4;2;<percent>` |
| `indeterminate` | `4;3` |
| `paused` | `4;4` or `4;4;<percent>` |

Only fixed state codes and validated integers cross the backend boundary.
Application strings can never become part of the control sequence.

### Retained terminal state and lifecycle

The runtime retains the most recently accepted state and percentage. A later
call replaces the complete report.

Before a successful App suspension releases the terminal, Cooper emits
`remove` without changing the retained request. A failed suspension restores
the retained progress. A successful resume re-emits the retained state after
Vaxis reacquires the terminal. App destruction removes active progress before
closing Vaxis, including destruction while suspended after Vaxis is successfully
resumed for cleanup.

The runtime lifecycle lock orders calls against notification requests,
suspension, resume, and close. Vaxis's synchronized terminal writer serializes
the control output with rendered frames. A racing update either emits before
the lifecycle transition or returns false afterward.

### Backend support

The initial backend enables progress only for terminals identified as Ghostty
through Vaxis terminal identity, or through `TERM_PROGRAM`/`TERM` when no
terminal identity is available. A nonempty terminal identity is authoritative.
tmux, GNU Screen,
and Zellij remain unsupported until Vaxis or Cooper can safely wrap the
sequence for the active multiplexer.

Operators may force or disable the capability:

```text
COOPER_TERMINAL_PROGRESS=1|true|on
COOPER_TERMINAL_PROGRESS=0|false|off
```

A multiplexer remains authoritative over a forced enable.

### Testing

`testing::new` supports `terminal_progress_supported: false`, records accepted
logical reports, and accepts an `on_terminal_progress` observer for deterministic
lifecycle tests. The observer runs inside the lifecycle transition and must not
re-enter Context or call `TestApp.suspend()`, `resume()`, or `destroy()`.
`TestApp.suspend()` and `TestApp.resume()` model the progress-relevant lifecycle transition without a
terminal. `TestApp.terminal_progress_reports()` returns an ordered snapshot and
remains readable after destruction. Headless suspension and teardown record the
automatic remove for active progress.

Go boundary tests validate every wire payload, detection, forced/disabled
behavior, multiplexer rejection, and invalid combinations. PTY coverage
validates OSC output plus remove/restore across App suspension.

## Consequences

Cooper can reproduce Kit's agent-turn indicator and expose the complete OSC 9;4
state model without leaking terminal codes into application logic. Persistent
progress cannot remain stale after normal suspension or teardown.

Support is intentionally Ghostty-only until other terminal behavior and
multiplexer transport are verified. The public API remains backend-independent
and can support additional terminals later.

## Related

- [ADR 0002: Define the Application API](./0002-define-application-api.md)
- [ADR 0009: Define Terminal-Mediated Notifications](./0009-define-terminal-mediated-notifications.md)
- [Kit terminal turn status](https://github.com/akonwi/kit/blob/main/docs/terminal-turn-status.md)
