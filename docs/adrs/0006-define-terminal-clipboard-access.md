# 0006: Define Terminal Clipboard Access

## Status

Accepted

## Context

Cooper exposes terminal paste events and a global read-only `Selection`, including
the selected plain text, but applications cannot copy text to the terminal host's
clipboard or request its current contents. Paste events are user-initiated input;
they are not a clipboard service and cannot implement copy, clear, or
programmatic reads.

Vaxis already implements OSC 52 clipboard writes and reads. `ClipboardPush`
base64-encodes text and emits an OSC 52 write. `ClipboardPop` emits an OSC 52
query and blocks with a Go `context.Context` until the terminal responds or the
context is cancelled. This preserves the correct host boundary for local and
remote applications: the terminal decides whether to allow, reject, prompt for,
or ignore each request.

Terminal clipboard policy is not a capability that Cooper should pre-negotiate.
Many terminals allow writes while guarding reads behind a preference or user
confirmation. OSC 52 does not acknowledge writes, and a terminal that ignores a
read may never respond.

## Decision

### App-bound clipboard service

Add an Ard-native public `clipboard.ard` module and expose one Clipboard from
each App:

```ard
struct App {
  context: mut context::Context,
  root: mut root::Root,
  clipboard: mut clipboard::Clipboard,
}

impl Clipboard {
  fn mut read() Str!Error
  fn mut write(value: Str)
  fn mut clear()
}
```

Clipboard is bound to the App's terminal and lifetime. Copies of the public
facade share one internal state.

### Imperative operation semantics

`read()` is intentionally blocking. It mirrors Vaxis's operation and keeps
fiber scheduling policy out of the primitive. Applications that must remain
responsive call it from an Ard fiber and use `Context.dispatch` before mutating
retained controls.

Only one read may be active for an App. OSC 52 responses have no request
identifier and Vaxis exposes one response channel, so a concurrent read returns
an error immediately rather than racing or silently serializing. A pending read
is cancelled as soon as irreversible App destruction is requested. A terminal
that prompts may take as long as the user needs; Cooper does not impose a default
timeout.

`write(value)` and `clear()` are infallible emission requests. Clear emits an
empty OSC 52 clipboard value. Vaxis and OSC 52 provide no observable terminal
acceptance or output error, so returning `Result` would imply a guarantee Cooper
cannot make. Calling either method after App destruction or while App is
suspended is a programmer contract violation and panics.

An empty successful read is valid and is not distinguishable from a terminal
that explicitly returns an empty clipboard. A terminal that ignores or blocks a
read leaves it pending until App destruction.

OSC 52 has no request IDs and an already emitted query cannot be recalled.
Therefore `App.suspend()` returns an Error while a Clipboard read is active
rather than allowing its late response to satisfy a post-resume read or reach
the program temporarily owning the terminal. An idle suspension makes Clipboard
unavailable before Vaxis releases terminal input. A successful App resume
creates a fresh read context and makes Clipboard available again. Vaxis suspend
failure restores Clipboard availability.

### Backend and ownership

Keep OSC 52 encoding, parsing, and terminal I/O in Vaxis. Add only a narrow Go
bridge beneath `ffi/core/backend/` to pair the Vaxis terminal with a cancellable
Go context, because Ard v0.38 cannot import Go's `(context.Context,
context.CancelFunc)` return shape from `context.WithCancel` directly.

Ard owns the public service, stopped/suspended-state validation, one-read guard,
and lifecycle ordering. Irreversible shutdown marks Clipboard stopped and
cancels its Go context immediately, including shutdown requested while the event
pump is blocked in a misuse of `read()`. Final resource cleanup joins the active
read before Vaxis closes. Pre-start signal shutdown follows the same ordering.

Writes are serialized against Clipboard teardown and suspension. Vaxis remains
responsible for serializing control output with terminal rendering.

### Headless behavior

`testing::TestApp` exposes the same Clipboard facade backed by deterministic
in-memory text. Tests can write, clear, and read without a terminal. Internal
blocking fakes validate concurrent-read rejection and teardown cancellation.

PTY coverage inspects emitted OSC 52 write, clear, and query sequences, sends a
synthetic OSC 52 response through Vaxis, and verifies clean App-lifetime
cancellation. These tests validate Cooper's request and response handling; they
do not claim that any terminal accepts clipboard access.

### Paste remains separate

`App.on_paste` and focused-control paste delivery remain unchanged. Clipboard
reads do not synthesize PasteEvents, and terminal paste does not call Clipboard.

## Consequences

Applications gain clipboard access without platform-specific commands or a
local/remote host ambiguity. OSC 52 support, permissions, prompting, limits, and
failure policy remain under terminal control.

A blocking read can remain pending indefinitely when the terminal ignores it.
Applications must place reads in fibers when UI responsiveness matters. App
destruction is the operation's cancellation boundary, and suspension is rejected
until the read completes. A future concrete use
case may add caller-controlled cancellation or timeout without changing write,
clear, or paste semantics.

Cooper does not initially invoke `pbcopy`, `wl-copy`, `xclip`, PowerShell, or
other platform commands. Such fallbacks would target the process host rather
than necessarily the user's terminal host and would behave incorrectly across
remote sessions.

## Related

- [ADR 0002: Define Application API](./0002-define-application-api.md)
- [ADR 0003: Define Interaction, Focus, and Selection](./0003-define-interaction-focus-and-selection.md)
- [Vaxis ClipboardPush and ClipboardPop](https://pkg.go.dev/go.rockorager.dev/vaxis#Vaxis.ClipboardPop)
