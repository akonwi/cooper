# 0012: Define Terminal Title Updates

## Status

Accepted

## Context

Terminal applications use the window or tab title to expose compact ambient
state such as an application name, unread count, active workspace, or current
resource. Tinear needs to update its Inbox count without importing Vaxis or
writing terminal control sequences from application code.

Cooper's Vaxis fork exposes `Vaxis.SetTitleAndIconName(string)`, which emits
OSC 0 but returns no delivery status and does not preserve the previous
terminal title. Terminal title-stack
save/restore protocols are inconsistent and are not represented by Vaxis.
Title content is an untrusted terminal control field, so Cooper must prevent
embedded control characters from terminating OSC 0 or injecting another
sequence.

Terminals differ in which title they display. Most keep one title that both
OSC 0 and OSC 2 set. Others, such as iTerm2, keep the window title (OSC 2) and
the icon name (OSC 1) separately and label tabs with the icon name, so OSC 2
alone never reaches the tab.

A title update is terminal chrome rather than a retained control. Runtime owns
App-lifetime terminal-mediated capabilities and is available to controllers and
background work through `application.context`.

## Decision

### Runtime API

Applications update the terminal title through Runtime:

```ard
let _ = application.context.set_title("Tinear · 3")
```

```ard
impl runtime::Runtime {
  fn mut set_title(value: Str) Bool
}
```

The method returns `true` when the App lifecycle accepts the request and
invokes, or has already invoked, the title backend for the same normalized
value. It returns `false` while stopping or after destruction. It does not
request a Cooper frame.

An empty string is an explicit request for an empty title. Cooper does not
interpret it as absence and does not add a separate clear operation.

### Title sequence

Cooper emits OSC 0, which sets both the window title and the icon name, so the
title labels the window or tab in every terminal that displays either.
Applications cannot set the two separately.

### Sanitization and coalescing

Cooper replaces every C0 or C1 control character with one space before the
value reaches Vaxis. This includes BEL, ESC, newlines, tabs, and string
terminators that could escape OSC 0. Ard strings are valid Unicode, so no
additional malformed UTF-8 boundary is needed.

The runtime retains the most recently emitted normalized value and coalesces
identical updates. The first update is always emitted, including an empty first
value.

### Lifecycle

Title updates are thread-safe and serialized with terminal suspend, resume, and
destruction. They are accepted before start, while active, and while suspended.
A request racing suspension waits for the transition and emits against the
resulting stable lifecycle state. Updates made while suspended emit immediately;
resume does not duplicate them.

Cooper intentionally leaves the last emitted title in place when the App is
destroyed. It does not query, save, blank, or restore a previous title. Adding
portable title-stack behavior would require a separate backend capability and a
new decision.

### Testing

`TestApp.terminal_titles()` returns the ordered normalized title emissions and
remains readable after destruction. Headless tests cover sanitization,
coalescing, empty titles, suspended emission, background-fiber serialization,
and rejection after destruction. PTY coverage verifies the OSC 0 bytes emitted
by Vaxis.

## Consequences

Applications can expose terminal title state without backend imports or raw
control strings. Runtime keeps the capability usable from long-lived
controllers and background work, while lifecycle rejection remains explicit.

The API cannot confirm that a terminal displayed the title because Vaxis and
OSC 0 provide no acknowledgement. Terminals that show the icon name somewhere
other than a tab, such as a minimized window label, show the title there too. Leaving the final title after process exit is
intentional and matches the selected lifecycle contract.

## Related

- [ADR 0002: Define the Application API](./0002-define-application-api.md)
- [ADR 0009: Define Terminal-Mediated Notifications](./0009-define-terminal-mediated-notifications.md)
- [ADR 0010: Define Terminal Progress Reporting](./0010-define-terminal-progress-reporting.md)
- [ADR 0013: Consolidate Context into Runtime](./0013-consolidate-context-into-runtime.md)
- [Vaxis fork](https://github.com/akonwi/vaxis/tree/cooper-distribution)
