# ADR 0013: Consolidate Context into Runtime

## Status

Accepted

## Context

Cooper originally exposed three application-level roles: App, Context, and an
internal application Runtime. Context owned retained Node registration and
layout ownership while forwarding dispatch, focus, terminal, and platform
capabilities to Runtime through injected callbacks. Moving retained ownership
into Runtime made Context a persistent wrapper with no independent state,
lifetime, or execution scope.

Gooey provides a useful contrast. Its `Cx` carries a current declarative
rendering builder, a typed application-state pointer, generated render IDs, and
other frame-local bindings. Its per-window `Window` is the retained runtime.
Cooper has one retained terminal tree and no frame-local declarative build
context, so an equivalent third type has no distinct responsibility.

## Decision

Cooper exposes two application-level types:

```text
App
├── context: Runtime
└── root: Root
```

`Runtime` is the single application-scoped capability and state owner. It owns
retained Node identity and registration, layout coordination, focus, selection,
routing, dispatch, cancellation, clipboard access, terminal state, lifecycle
synchronization, and platform services.

`App.context` is a mutable Runtime reference. The field name remains `context`
because it is the ergonomic handle applications pass to controls and retain in
controllers, but its type is `runtime::Runtime`; Cooper has no separate Context
type or `context.ard` module.

All controls accept Runtime directly:

```ard
fn new(runtime: mut runtime::Runtime, ...) Control
```

App owns the permanent Root and delegates start, wait, suspend, resume, and
destruction to its Runtime using that Root. Root accepts one Runtime during
construction, creates its Node through that Runtime, and binds itself back to
the same Runtime. Runtime validates Root identity before lifecycle startup.

The public Runtime struct exposes only the stable application capabilities that
are values (`clipboard`, `dispatch`, and `cancellation`) plus opaque internal
storage. Terminal backends, protocol callbacks, lifecycle phases, mutexes,
retained Nodes, and other mutable implementation state remain in a private
State inside `runtime.ard`. This private State is an implementation detail, not
a separate public ownership role.

Detached control tests use `runtime.new_detached`. A detached Runtime has no
terminal or URL opener, rejects dispatch, and performs complete deterministic
cleanup through `destroy_detached`.

All shared private State methods use mutable receivers so calls do not copy
synchronized application state before locking.

## Consequences

- The public ownership graph is `App -> Runtime`; there is no redundant Context
  wrapper or callback-by-callback Context factory.
- Existing application expressions such as `application.context.dispatch(...)`
  and `application.context.set_title(...)` remain ergonomic.
- Controls, Root, App, and TestApp all operate on one Runtime identity.
- Runtime is the final validation and synchronization boundary for platform and
  terminal operations.
- Applications importing the removed `cooper/context` module must import
  `cooper/runtime` and replace `context::Context` with `runtime::Runtime`.
- Cooper should introduce a new scoped context type only if a future execution
  model adds genuinely scoped state, such as a frame-local builder or a
  per-callback transactional scope.

## Related

- [ADR 0002: Define the application API](./0002-define-application-api.md)
- [ADR 0012: Define terminal title updates](./0012-define-terminal-title-updates.md)
- [Gooey `Cx`](https://github.com/duanebester/gooey/blob/main/src/cx.zig)
- [Gooey `Window`](https://github.com/duanebester/gooey/blob/main/src/context/window.zig)
