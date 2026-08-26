# 0009: Define Terminal-Mediated Notifications

## Status

Accepted

## Context

Cooper applications need to request desktop notifications for events such as a
completed build or background task. The process running Cooper is not always on
the user's desktop: it may run through SSH or inside a multiplexer. Invoking
`notify-send`, AppleScript, PowerShell, or another platform command would target
the process host rather than necessarily targeting the terminal user's desktop.

OpenTUI keeps this boundary terminal-mediated. Its
`renderer.triggerNotification(message, title?)` chooses OSC 99, OSC 777, or OSC
9 from terminal queries, terminal identity, environment hints, and explicit
overrides. It sanitizes protocol fields, wraps output for supported
multiplexers, and returns whether a protocol was selected and output queued. It
cannot observe whether the terminal or desktop displayed the request.

Vaxis exposes `Vaxis.Notify(title, body)`, but its behavior is narrower. An
empty title emits OSC 9 and a nonempty title emits OSC 777. It returns no status,
does not expose OSC 99 or notification capability detection, and does not add
notification-specific multiplexer passthrough. Cooper must not present this as
full terminal support or allow untrusted text to inject OSC fields.

Context is the Cooper capability already passed to control constructors and
background work. A separate notification service facade would add indirection
without owning a persistent resource or response stream like Clipboard does.

## Decision

### Context API

Add one notification method to Context:

```ard
let accepted = application.context.notify(
  "Build finished",
  title: "Cooper",
)
```

```ard
impl Context {
  fn mut notify(message: Str, title: Str?) Bool
}
```

An empty present title is normalized to an absent title. The message may be
empty. Cooper exposes no separate capability predicate: lifecycle can change
between a check and an emission, so the result of `notify` is authoritative.

`true` means Cooper selected an available terminal protocol and synchronously
invoked its emission backend. It does not mean the bytes were accepted by the
terminal or that a desktop notification appeared. `false` means no request was
emitted because the protocol is unsupported or the App is suspended, stopping,
or destroyed.

### Lifetime and concurrency

Notification requests may be made before App start, in Cooper callbacks, or
from background fibers. They do not mutate the retained tree and do not request
a frame.

The runtime lifecycle lock orders notification requests against suspension,
resumption, and final close. Vaxis's synchronized terminal writer serializes the
control output with rendered frames. Suspension marks notification output
unavailable before releasing the terminal. A failed suspension restores the
previous active phase; a successful resume makes notification output available
only after Vaxis reacquires the terminal. Destruction makes later requests
return false. A request racing a lifecycle transition either emits before that
transition or returns false after it.

### Backend selection

Keep protocol details beneath `ffi/core/backend/notificationbridge/`. The
initial bridge uses Vaxis's own output path and supports only protocols Vaxis can
emit safely:

- OSC 777 for detected Ghostty, WezTerm, Warp, hterm/Blink, Contour,
  VTE/rxvt-derived terminals, and Windows Terminal;
- OSC 9 for detected iTerm, Apple Terminal, and Terminal.app;
- no notification emission for unknown terminals, Kitty/foot OSC 99 paths, or
  tmux, GNU Screen, and Zellij sessions that require passthrough Cooper cannot
  request through Vaxis.

Terminal identity is stronger than environment hints. The bridge may use
Vaxis's terminal ID, `TERM_PROGRAM`, `TERM`, `TERM_FEATURES`, and `WT_SESSION`.
These environment overrides are supported for operational diagnosis:

```text
COOPER_NOTIFICATION_PROTOCOL=osc9|osc777|osc99|none
COOPER_NOTIFICATIONS=0|false|off
```

Forcing OSC 99 records an unsupported route until Vaxis exposes that protocol.
Multiplexer safety remains authoritative over a forced OSC 9 or OSC 777 because
Vaxis cannot wrap notification output for those sessions.

The bridge replaces malformed UTF-8, C0/C1 controls, DEL, and semicolons with
spaces so title and message cannot terminate or add protocol fields. OSC 9
combines a nonempty title and message as `title: message`. ConEmu is excluded
because its overloaded OSC 9 command forms make untrusted payloads unsafe.
Protocol selection and sanitization are not public Ard concepts.

The preferred long-term implementation is to move OSC 99/777/9 capability
selection, sanitization, and multiplexer passthrough into Vaxis. Cooper's Context
contract does not change when the backend gains that support.

### Headless testing

`testing::new` installs a deterministic supported notification backend by
default and accepts `notifications_supported: false` for fallback tests.
`TestApp.sent_notifications()` returns an ordered snapshot of accepted logical
requests:

```ard
struct Notification {
  message: Str,
  title: Str?,
}
```

Snapshots remain readable after TestApp destruction. Rejected requests are not
recorded. Go boundary tests validate protocol selection and wire sanitization;
PTY coverage validates live OSC output, disabled behavior, suspension, and
clean teardown.

### Deferred features

Cooper does not initially expose protocol enums, notification identifiers,
replacement, urgency, actions, click callbacks, icons, timeouts, notification
progress payloads, or receipt acknowledgements. OSC 9;4 terminal-surface progress
is specified separately by [ADR 0010](./0010-define-terminal-progress-reporting.md).
In-application toast controls are a separate visual
component concern and are not part of this API.

## Consequences

Applications can request desktop notifications through the same Context they
already pass to controls and fibers. The Bool result is truthful about Cooper's
emission route without claiming desktop delivery.

The initial implementation intentionally supports fewer terminals than
OpenTUI, notably excluding OSC 99 and multiplexers. This conservative behavior
avoids malformed output and false capability claims while preserving a stable
public API for a future Vaxis enhancement.

No host notification command is invoked, so local, SSH, and remote terminal
ownership remain unambiguous.

## Related

- [ADR 0002: Define the Application API](./0002-define-application-api.md)
- [ADR 0006: Define Terminal Clipboard Access](./0006-define-terminal-clipboard-access.md)
- [OpenTUI notifications](https://opentui.com/docs/core-concepts/notifications/)
- [Vaxis Notify](https://pkg.go.dev/go.rockorager.dev/vaxis#Vaxis.Notify)
