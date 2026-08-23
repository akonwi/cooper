# 0002: Define the Application API

## Status

Accepted

## Context

Cooper needs one coherent application-facing contract for constructing a
runtime, retaining controls, mutating the tree, handling input, scheduling
frames, and testing applications. The contract must remain Ard-native while
using Vaxis only as the terminal backend.

## Decision

### Model

Cooper follows OpenTUI core's imperative retained model: create one terminal
runtime, pass its Context to control constructors, build one persistent tree,
and mutate existing controls directly. Cooper owns layout, drawing, input, and
terminal output.

The application-facing core is defined here. `Renderable` remains a
language-visible implementation protocol under `core/`, not a supported custom
extension API yet.

### App, Context, and Root

```ard
let application = app::new().expect("create Cooper app")
let panel = box::new(application.context)
panel.add(text::new(application.context, content: "Hello"))
application.root.add(panel)
defer application.destroy()
application.run().expect("run Cooper app")
```

```ard
struct App {
  context: mut context::Context,
  root: mut root::Root,
}

fn new(
  exit_on_ctrl_c: Bool?,
  auto_focus: Bool?,
  use_mouse: Bool?,
) App!Error

impl App {
  fn start() Void!Error
  fn wait() Void!Error
  fn run() Void!Error
  fn suspend() Void!Error
  fn resume() Void!Error
  fn destroy()

  fn on_key(handler: fn(mut event::KeyEvent)) fn()
  fn on_paste(handler: fn(mut event::PasteEvent)) fn()
}
```

All three options default to `true`; `auto_focus` means focus on mouse-down.
App is a copyable facade over shared runtime state held through Context and
Root. Copies observe the same lifecycle.

`start` mounts the permanent Root, commits the initial frame when the terminal
is active, starts the App event pump, and returns. Repeated starts while the App
is live are idempotent. `wait` blocks until final destruction and is a
repeatable completion barrier; calling it before start returns an Error. `run`
is the standalone convenience `start` followed by `wait`. It does not itself
own teardown.

`destroy` is the only irreversible lifecycle operation and remains idempotent:
before start it abandons the App synchronously; after start it requests shutdown
at a safe event-loop boundary. `wait` observes completion of that cleanup. A
standalone caller using nonblocking `start` must call `wait` after `destroy`
before allowing its main function to return.
Ctrl+C with `exit_on_ctrl_c` enabled requests destruction. Starting after final
destruction returns an Error rather than panicking. If terminal release fails,
`wait` reports that backend Error and a repeated `destroy` retries the remaining
terminal cleanup without recreating application resources.

`suspend` synchronously restores terminal input and screen state while retaining
the Context, Root, controls, focus, selection, listeners, and queued model
updates. Rendering pauses and terminal input is not delivered while suspended.
`resume` reacquires the terminal, drains no stale pre-suspension input, forces a
resize-aware complete frame, and continues the same event pump. Both operations
are idempotent in their stable state, may be used before or after start, and
return backend errors. Destruction is valid while suspended. Cooper disables
Vaxis's internal signal handlers and routes resize signals through coalesced
runtime state and termination signals through serialized App destruction, so
they cannot race terminal lifecycle calls. Signals request App cleanup; Cooper
does not forcibly terminate a host process or its application fibers.

Because Ard application code and Cooper's event pump can run concurrently after
`start` returns, retained-tree mutation and listener registration after startup
must run in a Cooper callback or through `Context.dispatch`. Build the initial
tree before `start`; background fibers must not directly read or mutate controls.
This restriction does not apply while constructing the App before startup or to
TestApp's synchronous driver methods.

After destruction, listener registration, Root mutation, and construction
through the closed Context panic; dispatch is the exception and returns
`DispatchError`.

Root is permanently terminal-sized, uses column layout, and stretches children.
It cannot be styled, focused, reparented, or directly destroyed.

```ard
use cooper/core/node

impl Root {
  fn mut add(child: mut node::Renderable, index: Int?)
  fn mut remove(child: mut node::Renderable) Bool
  fn child_count() Int
}
```

Context is passed to constructors and exposes App-lifetime background-work
capabilities:

```ard
let _ = application.context.dispatch(fn() {
  status.set_content("Loaded")
})

application.context.cancellation.recv()
```

Dispatch queues an action on the UI thread. It may queue before `start` and is
also drained while the terminal is suspended; setters coalesce a frame for the
next active render. Dispatch after destruction is rejected, and queued actions
are suppressed by destruction. Cancellation closes during destruction. Cooper
does not own or forcibly terminate application fibers.

### Tree lifetime

Tree placement and destruction ownership are separate:

- `add(child)` appends and reparents;
- `add(child, index)` inserts or moves at a zero-based index;
- the index is interpreted after removing that child from its old position and
  may range from zero through the remaining child count;
- an invalid index panics;
- moving within one parent preserves attachment;
- moving between parents detaches and reattaches with a fresh scope;
- `remove` detaches a direct child without destroying it;
- `destroy()` destroys one control and detaches its children;
- `destroy(recursive: true)` destroys descendants first, then the control;
- App teardown destroys all remaining Context-owned controls.

Child order controls layout, drawing, and hit testing. Applications retain
direct control references; public IDs and string tree lookup are omitted.

### Common control API

Every visual control exposes:

```ard
fn style() style::Style
fn mut set_style(value: style::Style)
fn layout() geometry::Geometry
fn mut destroy(recursive: Bool?)
```

Interactive controls additionally expose:

```ard
fn mut focus() Bool
fn mut blur()
fn is_focused() Bool
fn mut on_key(handler: fn(mut event::KeyEvent)) fn()
fn mut on_paste(handler: fn(mut event::PasteEvent)) fn()
fn mut on_mouse(handler: fn(mut event::MouseEvent)) fn()
fn mut on_focus(handler: fn()) fn()
fn mut on_blur(handler: fn()) fn()
```

Control constructors return mutable references so the tree and application
share one persistent identity. Their shared `styles` named argument accepts the
common `style::Style` value. Effective setter changes request a frame.

### Style and geometry

Style is open value data. It has the standard Flexbox/OpenTUI vocabulary:

```ard
struct Style {
  foreground: color::Color?,
  background: color::Color?,
  border: Border,
  border_color: color::Color?,
  display: Display,
  position: Position,
  overflow: Overflow,
  flex_direction: FlexDirection,
  flex_wrap: FlexWrap,
  flex_basis: Length,
  flex_grow: Float32,
  flex_shrink: Float32,
  align_items: Align,
  align_self: Align,
  justify_content: Justify,
  width: Length,
  height: Length,
  min_width: Length,
  min_height: Length,
  max_width: Length,
  max_height: Length,
  top: Length,
  right: Length,
  bottom: Length,
  left: Length,
  padding: Edges,
  margin: Edges,
  gap: Length,
}
```

`style::new` accepts every field as a named optional parameter. Length helpers
are `cells`, `percent`, `auto`, `undefined`, `max_content`, `fit_content`, and
`stretch`. Foreground and background colors inherit through the retained tree;
an explicitly configured child color overrides its inherited color. A background
fills the complete node bounds. `set_style` validates the complete value.
Absolute positioning is exposed only with working edge offsets.

```ard
struct Rect {
  x: Int,
  y: Int,
  width: Int,
  height: Int,
}

struct Geometry {
  local: Rect,
  screen: Rect,
}
```

Local geometry is relative to the parent's unscrolled content origin; screen
geometry includes ancestor layout and scrolling. Geometry is zero before the
first frame and may remain stale until the next scheduled frame.

### Color

```ard
struct Color {
  red: Uint8,
  green: Uint8,
  blue: Uint8,
}

fn rgb(red: Int, green: Int, blue: Int) Color
```

Components outside `0...255` panic. `Color?` represents terminal default or no
fill according to the property. Alpha, named colors, palette indexes, and theme
references are deferred.

### Text

`TextStyle` and `Text` both live in `text.ard`.

```ard
enum TextWrap {
  none,
  character,
  word,
}

struct TextStyle {
  foreground: color::Color?,
  background: color::Color?,
  bold: Bool,
  dim: Bool,
  italic: Bool,
  underline: Bool,
  blink: Bool,
  reverse: Bool,
  strike: Bool,
}
```

```ard
text::new(
  application.context,
  content: "Important",
  wrap: text::TextWrap::word,
  styles: style::new(width: style::cells(30)),
  text_style: text::style(bold: true),
)
```

Text exposes content, wrapping, TextStyle, corresponding setters, and the common
control API. Common Style colors provide inherited element colors; explicitly
configured TextStyle colors override them for painted text. It supports explicit
newlines and terminal-width-aware word or grapheme wrapping. Graphemes are never
split. Rich spans, selection, links, truncation, Markdown, and Code are deferred.
ADR 0003 later adopts read-only selection; ADR 0005 adopts rich spans, links,
truncation, Unicode wrapping, and double-click word selection while keeping
Markdown and Code separate.

### Box

```ard
enum Border {
  none,
  single,
  double,
  rounded,
  heavy,
}

box::new(
  application.context,
  styles: style::new(
    border: style::Border::rounded,
    border_color: color::rgb(80, 120, 155),
  ),
  title: "Panel",
)
```

Box exposes indexed `add`, `remove`, `child_count`, the common control API, and
a title getter/setter. Border kind and color are part of the common Style;
Box's border convenience getters/setters update that Style. A border uses one
terminal cell and reduces the child content area through layout.

Box is not focusable by default. `set_focusable(true)` enables explicit focus
and keyboard listeners. Registering its first mouse listener enables hit
testing; removing its last mouse listener disables hit testing. Pointer
enablement is not public.

Partial/custom borders, bottom titles, and separate title styling are deferred.

### Input

```ard
input::new(
  application.context,
  value: "",
  placeholder: "Name",
  min_length: 1,
  max_length: 80,
  styles: style::new(width: style::cells(30)),
  text_style: text::style(),
  placeholder_style: text::style(dim: true),
)
```

Input exposes getters/setters for value, placeholder, minimum/maximum grapheme
length, TextStyle, and placeholder TextStyle, plus:

```ard
fn mut submit() Bool
fn mut on_input(handler: fn(Str)) fn()
fn mut on_change(handler: fn(Str)) fn()
fn mut on_submit(handler: fn(Str)) fn()
```

Editing and changed `set_value` calls emit input. Focus records a commit
baseline. Blur emits change only when the value changed. Successful submit emits
a pending change, updates the baseline, and then emits submit, so a following
blur does not duplicate change. Submit returns false below `min_length`.

Input removes newlines, applies `max_length`, and keeps cursor movement and
editing grapheme-safe. `set_value` moves the cursor to the end. A TextStyle
background fills the complete Input bounds. Cursor appearance remains runtime
policy. ADR 0004 extends this accepted base with an Ard-native editor action
model and readline-style default keybindings.

### ScrollBox

ScrollBox is a vertical container with the Box tree operations and common
control API:

```ard
fn scroll_top() Int
fn requested_scroll_top() Int
fn maximum_scroll_top() Int
fn scroll_height() Int
fn mut scroll_to(y: Int) Bool
fn mut scroll_by(delta: Int) Bool
fn mut scroll_child_into_view(child: mut node::Renderable) Bool
```

The requested offset persists across layout changes; the effective offset is
clamped. Wheel input stops bubbling only when scrolling moves, allowing nested
fallback. ScrollBox is focusable and handles arrows, Page Up/Down, Home, and
End.

Horizontal/sticky scrolling, scrollbars, acceleration, and viewport culling are
deferred.

### Events, listeners, and focus

Cooper converts Vaxis input to backend-independent values. Key events contain a
canonical string name, text, press/repeat/release type, and Shift/Ctrl/Alt/Super
modifiers. Paste is separate. Mouse events contain typed down/up/move/drag/drop/
over/out/scroll kinds, button, global and local coordinates, modifiers, and
scroll deltas.

Event listeners receive one shared mutable event reference. Events provide:

```ard
fn mut stop_propagation()
fn mut prevent_default()
fn is_propagation_stopped() Bool
fn is_default_prevented() Bool
```

Mouse input targets the hit control and bubbles through parents; there is no
capture phase. At each control, listeners run before that control's built-in
mouse behavior. Preventing default suppresses that behavior, including
ScrollBox wheel movement, while stopping propagation ends later delivery. Mouse
autofocus happens after bubbling and may also be prevented.

Keyboard input runs through App listeners and then the focused control.
Stopping propagation stops later delivery. Preventing default allows later App
listeners but suppresses focused-control built-in behavior.

`on_*` methods register listeners in order and return idempotent removal
functions. Destroying a control removes its listeners. Control key listeners
run before built-in behavior. The initial general mouse listener receives a
MouseEvent; event-specific helpers are deferred.

App starts with no focus. Focus is explicit or caused by mouse autofocus. Blur,
hide, detach, or destruction clears focus without selecting a fallback.
Successful focus reveals through ancestor ScrollBoxes. Cooper has no implicit
Tab traversal.

### Frame scheduling

Cooper is demand-driven. Initial start, tree changes, effective setters, focus,
and resize request frames. Internal requests coalesce before layout and complete
logical-buffer drawing; Vaxis diffs terminal cells. Requests made during
suspension remain coalesced until resume forces a complete frame.

Dispatch itself does not force a frame; setters called by a dispatched action
do. Manual redraw, continuous rendering, frame-rate controls, and animation are
deferred.

### Testing

```ard
let test_app = testing::new(width: 40, height: 10)
let message = text::new(test_app.context, content: "Hello")
test_app.root.add(message)
test_app.render()
testing::assert_contains(test_app.frame().text(), "Hello")
test_app.destroy()
```

TestApp is an App-style value facade with Context and Root. Its non-mutating
methods operate on shared test-runtime state. It provides explicit render,
bounded flush, resize, key/paste/mouse/scroll input, read-only frame and cell
snapshots, and idempotent destruction. It never initializes the host terminal.
PTY tests retain responsibility for Vaxis parsing and terminal restoration.

### Errors

- Recoverable terminal creation, startup, suspension, resume, completion, and
  rejected dispatch use Result.
- Invalid arguments, tree invariants, and destroyed-control use panic.
- Expected conditional outcomes such as remove, submit, focus, and
  scroll-at-boundary use Bool.
- App, control, TestApp, and listener cleanup are idempotent.

### Modules

Documented application modules are:

```text
app  box  color  context  event  geometry
input  root  scroll_box  style  testing  text  ui
```

`ui` provides direct constructor and type aliases for built-in controls, such
as `ui::input`, `ui::text`, and `ui::box`, so applications can import controls
through one module. The control modules remain available individually.

Public modules own their complete Ard domain model and supporting logic. Only
unsupported runtime mechanisms with no public counterpart—Node, paint, focus,
hit testing, routing, scheduling, and application runtime—remain under `core/`.
Backend bindings remain under `ffi/core/backend/`. Ard does not enforce
package-private imports, so these paths communicate support boundaries rather
than enforcing them.

### OpenTUI correspondence

| OpenTUI core | Cooper |
| --- | --- |
| `createCliRenderer()` | `app::new()` |
| renderer root | `App.root` |
| renderer as RenderContext | narrow `App.context` capability |
| imperative renderable constructors | retained control constructors |
| indexed `add` and direct mutation | indexed `add` and setters |
| `renderSelf()` | internal `draw()` |
| renderer startup / host waiting | `App.start()` / `App.wait()` or `App.run()` |
| renderer suspension / resume | `App.suspend()` / `App.resume()` |
| renderer destruction | `App.destroy()` |
| test renderer | `TestApp` |

Cooper intentionally differs by separating App from Context, retaining a
blocking `run` convenience for Ard's process model, and deferring supported
custom-renderable authoring. Unlike OpenTUI's JavaScript host, an Ard main
function exits even while background fibers exist, so standalone applications
must call `run`, `wait`, or otherwise keep their process alive.

## Consequences

- The implementation, examples, tests, and package layout must migrate together
  to this clean-break API.
- Applications use persistent mutable controls and explicit tree operations.
- The initial public surface stays intentionally narrow, with deferred features
  added only after concrete use demonstrates a stable shape.
- Internal Renderable authoring remains unsupported until built-in controls have
  fully exercised the protocol.

## Related

None.
