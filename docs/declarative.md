# CUI: declarative components

`cooper/cui` is an **experimental, opt-in framework layer** requiring Ard
0.42.0. It reconciles view descriptions onto Cooper controls; the imperative API
and Cooper's layout, focus, editing, event, and terminal behavior are unchanged.

Run the complete example from `examples`:

```sh
ard run declarative_jobs.ard
python3 test_declarative_jobs.py
```

The larger `ard run cui_tinear.ard` example is a static-data slice of
[tinear](https://github.com/akonwi/tinear): a three-column issue board, local
filtering, and focused detail components with Description/Comments sections.
Run `python3 test_cui_tinear.py` to exercise its keyboard workflow.

## API shape

A component stores ordinary mutable state and the mutable props reference passed
to its constructor, then implements one method:

```ard
use cooper/cui as d

struct CounterProps {
  label: Str,
}

struct Counter {
  props: mut CounterProps,
  count: Int,
}

fn counter(props: mut CounterProps) mut Counter {
  (mut Counter{props: props, count: 0})
}

impl d::Component for Counter {
  fn mut render() d::View {
    d::box([
      d::text("{self.props.label}: {self.count}"),
      d::input("", on_submit: fn(value: Str, ctx: d::Context) {
        self.count =+ 1
      }),
    ])
  }
}

let view = d::child(counter, CounterProps{label: "Count"})
let renderer = d::mount(application.context, application.root, view)
defer renderer.destroy()
```

The central signatures are:

```ard
fn child(create: fn(mut $P) mut $C, props: $P, key: Str?) View
fn mount(runtime: mut Runtime, root: mut Root, view: View) Renderer
```

Both child types are inferred. Props are ordinary values, not framework wrappers.
The component stores the supplied `mut Props` reference so reconciliation can
update it before each render. The constructor runs only when that component
identity mounts. `mount` accepts either a primitive view or a child view as its
root, renders synchronously, and attaches retained controls.

Treat props as read-only input. Ard requires `mut Props` for the shared reference,
but does not enforce a read-only view of it. Keep state in separate component
fields; copying props during construction creates an initial snapshot rather
than a field that receives subsequent props updates.

There is no compiler-enforced generic bound requiring `$C` to implement
`Component`; Cooper verifies the erased value with a checked cast internally.
The same implementation technique updates typed props and keeps recursive
`View` descriptions opaque. Invalid component/props combinations are programmer
errors.

## Identity and reconciliation

Within one retained parent, a keyed child component is identified by its key,
concrete component type, and props type. An unkeyed child is identified by its
position and those types. Factory function identity is deliberately not part of
identity: two factories returning the same concrete component type for the same
props type retain the existing instance, so the replacement initializer does
not run. Changing the parent creates a new identity.

Components may return components nested in arbitrary child lists. The renderer
automatically owns the expanded component tree; application code does not manage
separate child lifetimes. Keyed moves preserve component state and retained
control identity, including focus, selection, editor cursor, and scrolling.

For a collection, build an ordinary list of views:

```ard
let children = mut List::new<d::View>()
for job in self.jobs {
  children.push(d::child(job_row, JobProps{job: job}, key: job.id))
}
d::box(children.@)
```

Keys must be unique among siblings. Prefer stable item IDs to indexes when items
can move. A description that is never returned in the committed tree never mounts.

Reconciliation uses the next committed snapshot. Removing and reinserting an
identity before the next coalesced commit does not retire it. Once a removal is
committed, later reinsertion constructs a fresh component with fresh controls.

Hiding is different from removal. A keyed page wrapped in a box with
`display: ui::Display::none` stays mounted: component state, refs, and context
remain live, and queued work still delivers. Showing it again does not rerun
`mounted`. Remove the page from the returned list to close it and cancel its
context. The tinear example uses this distinction for retained issue tabs;
the application stores tab data and an active ID, not component instances.
Describe focus only on the active page. Hidden pages still render on updates;
this is retained identity, not an offscreen-rendering optimization.

Primitive identity uses key and kind, or unkeyed position and kind. The initial
surface is deliberately small:

| Constructor | Supported properties |
| --- | --- |
| `text(content, ...)` | String or rich TextContent, style, TextStyle, wrapping, overflow, key |
| `input(value, ...)` | Controlled value, placeholder, style, focused, input/submit/key/mouse callbacks, InputRef, key |
| `box(children, ...)` | Children, style, title, focused, key/mouse callbacks, BoxRef, key |
| `scroll_box(children, ...)` | Children, style, key/mouse callbacks, ScrollBoxRef, key |

Styles and common values come from `cooper/ui`. A `View` is a description, not a
control handle.

## Updates and effects

Event callbacks mutate ordinary component fields. Cooper schedules one coalesced
root render after managed input, submit, key, or mouse delivery. External UI-thread
work uses:

```ard
renderer.update(fn() {
  model.replace(next)
})

renderer.invalidate()
```

`update` runs work and schedules rendering; `invalidate` only schedules. Both are
UI-thread operations. `dispatch(fn() { ... })` is background-safe: Runtime queues
the closure onto the UI thread and a render follows it. Cancellation covers only
the renderer lifetime, not individual components. Component workers should use
the mount-scoped `ctx.dispatch` supplied to their lifecycle hook instead.

Constructors and `render` must be deterministic and effect-free. Rendering may
describe callbacks but must not subscribe, acquire resources, or mutate renderer
ownership. The renderer is root-driven rather than fine-grained or dependency
tracked.

## Lifecycle and resources

`d::Lifecycle` is optional:

```ard
impl d::Lifecycle for Counter {
  fn mut mounted(ctx: d::Context) {
    // Acquire this component's subscriptions or resources.
  }

  fn mut unmounting(ctx: d::Context) {
    // Release resources acquired by this component.
  }
}
```

`mounted` runs child-first after controls and refs are attached. It is not a
geometry hook: layout has not necessarily run. Mutations in lifecycle hooks
schedule one follow-up render. On retirement, all callbacks in the retiring
subtree are canceled first; controls and refs are then disposed child-first, and
`unmounting` runs child-first. Root cleanup follows the same rules on explicit
renderer destruction or Runtime teardown; suspension does not unmount it.

The framework owns component children and their dispatch lifetimes. Components
own their workers and external resources. Cleanup functions should remain
idempotent.

## Simulated asynchronous operations

Lifecycle hooks receive `Context`. All built-in event callbacks receive it as
their final argument: `on_input(value, ctx)`, `on_submit(value, ctx)`,
`on_key(event, ctx)`, and `on_mouse(event, ctx)`. `render()` stays context-free.
For example, an event handler can call `self.load(ctx, false)` directly without
storing context or binding a function in `mounted`.

Each component has one context lifetime, whether or not it implements Lifecycle.
Primitive descendants inherit their nearest enclosing component's context;
primitives outside components use the renderer lifetime. Keyed moves retain the
context, while removal retires it. `unmounting(ctx)` receives that same context
after cancellation, so dispatch from cleanup is rejected.

Components start ordinary `ard/async` workers; CUI provides no task runner or
timer abstraction. For example, with an application-defined `fetch_issue`:

```ard
fn mut mounted(ctx: d::Context) {
  let issue_id = self.props.issue.id
  let dispatch = ctx.dispatch
  async::start(fn() {
    let result = fetch_issue(issue_id)
    let _ = dispatch(fn() {
      self.result = result
      self.loading = false
    })
  })
}
```

Capture request inputs and the dispatch function before starting the worker.
Access mutable component state only inside the dispatched callback. `dispatch`
is background-safe, returns `Void!DispatchError`, and automatically schedules a
render after delivery. A successful return means queued, not guaranteed delivery.
The mount is checked both when posting and when executing: unmount suppresses
already-queued callbacks as well as rejecting new posts. Old handles never become
valid again after reinsertion. Renderer and Runtime destruction also retire them.

`ctx.cancellation` is a receiver closed before unmount cleanup. Workers may select
on it to stop waiting, or adapt it to a network client's cancellation mechanism.
Dispatch safety does not require the worker to cooperate, but unmount cannot
forcibly interrupt an arbitrary blocking request. Within a still-mounted component,
use a request counter or explicit cancellation to ignore superseded responses.

Suspension does not unmount a component or stop its workers; wall-clock waits
continue, unlike the removed animation-clock timer API. UI dispatch follows the
Runtime's suspension behavior. Tests can synchronize worker completion with
channels and then call `flush()` without wall-clock sleeps.

The tinear example simulates detail loading (650ms), failure (250ms), retry, and
board refresh (700ms). Press r to refresh/reload, or f in detail to inject a
failure. No network calls occur; the issue data stays static.

## Component-owned animations and dragging

Start a one-shot animation from a lifecycle or event callback:

```ard
let cancel = ctx.animate(
  250,
  fn(frame: animation::Frame) {
    self.offset = animation::lerp_int(40, 0, frame.progress)
  },
  ease: animation::out_quad,
)
```

Import `cooper/animation` for frames, easing, and interpolation. Duration is
positive milliseconds and easing defaults to linear. Frames run on the UI
thread and invalidate CUI automatically. `cancel()` is idempotent; retaining it
is optional because completion, component unmount, and renderer destruction
release the animation's callbacks. Starting an animation on a retired context
does nothing. Both `animate` and cancellation are UI-thread-only; workers must
use `ctx.dispatch`. Animation time follows Runtime suspension, unlike a
wall-clock async wait. Hidden components remain mounted and keep animating.

The Tinear confirmation toast demonstrates animation state without a timer loop
or manual unmount cleanup. Each replacement has a new key, so the old toast's
animation and async expiration cannot affect the replacement.

Drag handling uses ordinary `on_mouse` callbacks. Cooper captures left-button
drags to their pressed retained node, sends `drag_end` to the source, and sends
`drop` to the physical destination. CUI preserves that capture across matching
renders. Keep the source attached until release; use refs and screen geometry
when a floating overlay obscures the physical destination. App-specific drag
thresholds, drop eligibility, and data mutation remain component state.

Use `cui::text(..., selectable: false)` for draggable labels. Text is selectable
by default, and text selection takes precedence over ordinary drag capture.
The property can also be changed during reconciliation.

## Inputs, refs, and validation

Use `focused: selected` on a box or input to describe focus with state, rather
than assigning refs just to focus controls. `true` requests focus after the tree
is attached and lifecycle hooks run; `false` blurs that control only. Omit the
property to leave focus unmanaged. Declare at most one true target per active
screen. A box with a `focused` property is focusable even without a key handler.
Focus also reveals the control through nested scroll containers after layout.
Startup retries focus when the Runtime starts accepting requests.

CUI key callbacks run from the focused view outward through its declared
ancestors, including across component boundaries. Each callback receives its
own component's context. `stop_propagation()` stops ancestor callbacks;
`prevent_default()` separately suppresses the focused control's built-in action
(such as input editing). This is CUI routing, not a change to Cooper's imperative
key dispatch. Mouse events retain Cooper's existing bubbling behavior.

An input is controlled: write accepted `on_input` values into component state.
If a callback leaves the model unchanged, reconciliation restores the described
value. Equal and normalized values avoid unnecessary setters, preserving cursor
and selection state.

Use `d::input_ref()` for imperative capabilities such as focus. A ref does not
own its control, is populated before lifecycle mounting, and is cleared when the
view retires. It cannot be attached to two expanded inputs simultaneously.

`d::box_ref()` provides the same lifetime rules for a `box`. A box with an
`on_key` handler is focusable; use `ref.current.map(fn(panel) { panel.focus() })`
after mounting when imperative focus is needed. This lets a component own
keyboard navigation without a dummy input or a global listener. Merely providing
a ref does not make a box focusable. Removing both the handler and `focused`
property removes focusability.

`d::scroll_box_ref()` exposes a ScrollBox under the same ownership rules. Use
`ref.current.map(fn(panel) { panel.scroll_by(10) })` to scroll a preview without
moving focus from a list. Reconciliation preserves scroll position; removal
clears the ref and destroys the control. Duplicate and cross-renderer attachment
are rejected before the retained tree is mutated.

Duplicate sibling keys and duplicate refs are validated across the fully expanded
component view before controls or refs are mutated. Violations panic. Exceptions
from application constructors, rendering, or lifecycle hooks are also programmer
errors; Cooper makes no transactional model rollback or recovery promise.

Select, TextArea, images, animations, custom control adapters, fine-grained
scheduling, and a framework-managed background executor are not exposed.
