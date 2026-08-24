# 0003: Define Interaction, Focus, and Selection

## Status

Accepted

## Context

ADR 0002 established Cooper's retained application API and intentionally left
parts of interaction and text selection deferred. Cooper now has typed key,
paste, and mouse events; clipped hit testing; bubbling; explicit focus; mouse
autofocus; and deterministic headless input. Those pieces are useful, but they
do not yet form one complete interaction model.

The target behavior is OpenTUI Core's documented interaction contract:

- rendered controls participate in hit testing;
- mouse events bubble from the hit target;
- left-button drag capture has a stable source and drop target;
- each renderer owns one focused control and one global text selection;
- terminal-window focus remains separate from control focus;
- headless interaction exercises the same behavior as live interaction.

OpenTUI's implementation was reviewed in addition to its documentation. In
particular, its renderer owns pointer capture, hover reconciliation, focus,
and global selection, while renderables provide local selection behavior.
Cooper should match those observable semantics where they fit its Ard-native
API, not copy OpenTUI's TypeScript or native hit-grid architecture.

The current Cooper implementation has these concrete gaps:

- live and TestApp mouse paths are different;
- drag movement is hit-tested instead of being captured to its left-button
  source;
- right and middle drags can incorrectly produce drag-end and drop events;
- hover is not reconciled after layout changes;
- autofocus does not walk to the nearest focusable ancestor and is not limited
  to the left button;
- only pointer-enabled controls participate as final hit targets;
- sibling stacking has no `z_index`;
- terminal focus reports are ignored;
- there is no selection API;
- Text and Input do not support selection;
- TestApp cannot exercise the complete live pointer state machine.

Vaxis already reports mouse input and exposes `FocusIn` and `FocusOut`. It does
not expose an option equivalent to OpenTUI's movement-only reporting toggle;
its options only enable or disable mouse reporting as a whole.

## Decision

### Scope and compatibility target

Cooper will provide semantic parity for the interaction contract, while keeping
these deliberate API differences:

- Cooper continues to expose one typed `on_mouse` listener rather than nine
  event-specific listener methods.
- Cooper uses Ard tree traversal for hit testing rather than OpenTUI's native
  hit grid.
- TestApp injects backend-independent semantic input; PTY tests continue to own
  validation of Vaxis terminal parsing.
- Public mouse events expose no control, route, or drag-source identity. The
  listener registration identifies the current control, while source capture
  remains an internal runtime concern.
- Cooper does not add a movement-only App option until Vaxis can actually
  control that terminal mode. Silently discarding motion events would not
  provide the resource behavior promised by such an option.

All pointer, focus, terminal-focus, and selection behavior remains Ard-owned.
The Vaxis boundary only converts backend events.

### Public interaction values

`MouseEvent` retains its current fields and adds only drag state:

```ard
struct MouseEvent {
  event_type: MouseEventType,
  button: MouseButton,
  x: Int,
  y: Int,
  local_x: Int,
  local_y: Int,
  modifiers: Modifiers,
  scroll_x: Int,
  scroll_y: Int,
  is_dragging: Bool,
  internal_state: Any,
}
```

`is_dragging` distinguishes selection-drag delivery from ordinary motion. `x`
and `y` remain global cells. `local_x` and `local_y` are rebound before each
control's listener and built-in handler. The listener registration or captured
control reference already tells application code which control is current, so
Cooper does not expose target, current-target, or drag-source identities.

Events synthesized for over, out, drag-end, and drop have independent
propagation/default state. Retaining a mutable event beyond its callback is not
supported because bubbling continues to update local coordinates.

Terminal-window focus adds one independent value:

```ard
enum TerminalFocus {
  gained,
  lost,
}
```

Terminal focus never changes the focused control.

### Hit testing and stacking

Every live, displayed, non-Root control participates in hit testing, even when
it has no mouse listener. This lets events start at the deepest visible child
and bubble to interactive ancestors, makes selectable Text hittable, and lets
autofocus find a focusable ancestor.

Root remains a structural viewport and is never a mouse target. Hidden and
destroyed controls do not participate. `overflow: hidden` and `overflow:
scroll` continue to clip descendants; visible overflow continues to permit
children outside the parent's own bounds.

Style adds:

```ard
struct Style {
  // existing fields
  z_index: Int,
}
```

`style::new` defaults `z_index` to zero. It does not send this value to Yoga.
Sibling order has three distinct meanings:

- `children` remains layout, indexed mutation, focus, and document order;
- paint order is stable ascending `z_index`, then child order;
- hit order is the reverse of paint order.

Node caches stacking order and invalidates it on structural changes or a child
`z_index` change. It must not sort the layout children list in place.

### One shared pointer state machine

`core/pointer.ard` owns pointer state and its validated attachment handle:

```ard
struct AttachmentHandle {
  target: mut node::Node,
  root: mut node::Node,
  attachment_generation: Int,
}

impl AttachmentHandle {
  fn same(other: AttachmentHandle) Bool {
    self.target == other.target and
      self.root == other.root and
      self.attachment_generation == other.attachment_generation
  }
}
```

Whole-handle or optional-handle `==` is invalid because handles contain mutable
references; callers use `match` and `same`.

```ard
struct State {
  hovered: AttachmentHandle?,
  pressed: AttachmentHandle?,
  captured: AttachmentHandle?,
  dragging: Bool,
  has_pointer: Bool,
  x: Int,
  y: Int,
  modifiers: event::Modifiers,
}
```

Both live Vaxis events and `TestApp.mouse` call the same state machine. Runtime
code no longer has a second simplified headless mouse path.

An `AttachmentHandle` is validated before every use. Its Node must remain live
and mounted beneath the recorded Root with the recorded attachment generation. Destruction,
detachment, cross-parent reattachment, or movement to another Root invalidates
the handle. Same-parent indexed reorder preserves it because attachment is
preserved. Mutation during bubbling continues to use router generation checks.
All pointer handles are cleared during App destruction.

The state machine observes these rules:

1. There is no synthetic click event. Click and double-click remain down/up
   sequences.
2. Scroll targets the control under the pointer. If no control is hit, it falls
   back to the currently focused control. It does not alter hover or capture.
3. Over and out describe changes to the top hit target and bubble normally.
   Immediate transitions run only for physical move and drag. Down, up, and
   scroll update the remembered pointer coordinates and modifiers but do not
   themselves synthesize hover; scroll also leaves press/capture state alone.
   Post-frame geometry reconciliation may still emit a transition after any
   committed layout change. Over/out are not enter/leave events.
4. An ordinary left-button down not owned by selection records the hit target
   as the potential drag source.
5. The first left-button drag captures that source. Later drag events route to
   the captured source, while hit testing still determines hover and drop.
6. The captured source does not receive out merely because the pointer leaves
   it. Hit testing still drives over and drop on the physical control, but
   those public events carry no source identity.
7. When source and physical target differ, release dispatches fresh routes in
   this exact order: drag-end to source, up to source, drop to target, then up
   to target. With no physical target, only source drag-end and up run. When
   source and target are the same, the exact order is drag-end, drop, then one
   up; up is never delivered twice.
8. Every derived route has independent propagation and default state. Stopping
   drag-end propagation cannot suppress drop or either up route.
9. Right- and middle-button drags never capture. Their drag events follow hit
   testing and produce ordinary hover transitions, with no synthetic drag-end
   or drop.
10. If capture becomes invalid during a callback, capture ends safely and no
    later event is sent to the invalid control.
11. Ending or invalidating capture immediately reconciles hover at the last
    pointer position. A frame that changes hit geometry does the same. If the
    top target changed, Cooper emits out and over without requiring physical
    movement. Reconciliation is skipped only while capture remains valid.

Derived event outcomes are merged so redraw, quit, and focus-reveal behavior
from any over/out/drag-end/drop/up route is preserved.

### Propagation and default behavior

Mouse delivery remains target-first and bubbles through current parent links.
At each control, user listeners run before the built-in control handler. After
listeners return, the router revalidates the route, attachment generation,
display state, and event eligibility before invoking that built-in handler. A
listener that hides, destroys, detaches, or reparents the current control cannot
cause stale built-in behavior. Autofocus performs the same validation after the
complete route. `stop_propagation` prevents delivery to later ancestors but
does not undo work already performed.

Mouse `prevent_default` is aligned with OpenTUI's renderer-level contract. It
prevents:

- left-button autofocus after bubbling;
- clearing an existing selection after an ordinary left-button down.

It does not suppress built-in mouse handlers such as Input cursor placement or
ScrollBox wheel movement. Key and paste `prevent_default` continue to suppress
the focused control's built-in key or paste behavior.

Starting a selection happens before mouse-down delivery. Preventing default
therefore does not undo a selection that has already started.

### Control focus

Cooper continues to own exactly one focused control per App. Focus remains
explicit, with no automatic Tab traversal or fallback after blur, hide, detach,
or destruction.

Mouse autofocus changes to:

- only left-button down can autofocus;
- it runs after the complete bubbling route;
- it is skipped when default was prevented;
- it walks from the original hit target through its ancestors and focuses the
  first focusable control;
- focusing a different control blurs the previous one first;
- successful focus continues to reveal through ancestor ScrollBoxes.

Cooper does not add renderer-wide focused-control identity or focus-change
callbacks. Applications observe focus through each interactive control's
existing `is_focused`, `on_focus`, and `on_blur` API. Focus and blur listener
iteration continues to use snapshots so disposal and reentrant focus requests
are safe. Reentrant requests produce subsequent committed changes rather than
exposing an intermediate two-focused state.

### Terminal-window focus

Vaxis `FocusIn` and `FocusOut` events are converted to `TerminalFocus` and
published independently of control focus:

```ard
impl App {
  fn terminal_focus() event::TerminalFocus?
  fn on_terminal_focus(handler: fn(event::TerminalFocus)) fn()
}

impl TestApp {
  fn terminal_focus() event::TerminalFocus?
  fn on_terminal_focus(handler: fn(event::TerminalFocus)) fn()
  fn set_terminal_focus(value: event::TerminalFocus)
}
```

The state is initially unknown. Duplicate reports are coalesced. Terminals that
do not support focus reports simply leave the value unknown and emit nothing.
The pinned Vaxis release enables DEC focus reporting independently of
`DisableMouse`; PTY coverage pins that behavior for `use_mouse: false`. If a
future backend cannot enable focus reports independently, Cooper leaves terminal
focus unknown rather than coupling it to mouse input. A terminal blur does not
blur a control.

### Public selection model

A new root module, `selection.ard`, owns backend-independent selection values.
`geometry.ard` adds `Point`.

```ard
struct Point {
  x: Int,
  y: Int,
}

struct Range {
  start: Int,
  end: Int,
}

struct Selection {
  anchor: geometry::Point,
  focus: geometry::Point,
  bounds: geometry::Rect,
  selected_text: Str,
  is_dragging: Bool,
}
```

Global anchor, focus, and bounds use terminal cells. Bounds include both
endpoint cells. Local ranges are half-open display-cell offsets. Newlines add
one offset. Offsets are not UTF-8 byte indexes and always snap to complete
grapheme clusters, including wide graphemes.

App and TestApp expose immutable snapshots:

```ard
fn selection() selection::Selection?
fn clear_selection()
fn on_selection_change(handler: fn(selection::Selection?)) fn()
```

`is_dragging` makes the final committed snapshot observably different from its
last active-drag snapshot. A finished drag emits that final value once.
Clearing, extending, content mutation, layout mutation, and destruction also
emit only when the complete observable snapshot changes. Listener iteration
uses a snapshot. Reentrant selection mutations are queued and applied after the
current notification, preserving serialized mutation order. They request
another frame and their notifications remain queued until that frame commits;
Cooper never
publishes a selection snapshot that has not been painted. Observable-change
checks compare public Selection fields explicitly. They never apply `==` to
`SelectionResult` or fragment lists, which are not whole-value comparable under
Ard's list rules. Listener removal functions are idempotent.

Cooper does not initially expose `selected_renderables`: there is no supported
public Renderable supertype. `selected_text` is assembled in visual reading
order: top-to-bottom, then left-to-right; fragments on one visual row are
joined directly and different rows are joined with newlines.

### Selection runtime and control protocol

`core/selection_state.ard` owns one global selection per runtime. Its anchor
stores a Node reference, owning Root reference, and coordinates relative to the
control, but not an attachment generation. Validation walks the current parent
chain to the recorded Root. This lets an anchor survive same-Root reparenting
while still clearing on detach, destruction, or movement to another Root. The
selection runtime does not import `core/pointer`:

```ard
struct Anchor {
  control: mut node::Node,
  root: mut node::Node,
  local_x: Int,
  local_y: Int,
}
```

It tracks the active selection container and expands toward Root as the pointer
leaves the current subtree, matching OpenTUI's cross-control drag behavior.

Selection traversal uses the same effective ancestor clipping and `display`
rules as painting. Destroyed, hidden, detached, and fully clipped controls do
not contribute fragments. Overlapping visible selectable controls may both
contribute; fragments are ordered by visual row and x position, with document
order as the stable tie-breaker rather than `z_index`.

A same-Root reparent keeps the anchor and recomputes its global position. If the
anchor is destroyed, hidden, detached at reconciliation, moved to another Root,
or made non-selectable, the whole global selection clears. Making a non-anchor
control non-selectable clears its local state and removes only its fragments.
Controls clear local selection before unregistering selection callbacks.
Content and layout changes recompute from the original relative anchor and
current global focus.

Node exposes unsupported selection hooks without importing either public or
runtime selection modules. The internal protocol lives in `core/node.ard`:

```ard
struct LocalSelection {
  anchor_x: Int,
  anchor_y: Int,
  focus_x: Int,
  focus_y: Int,
  clip: geometry::Rect,
  is_active: Bool,
}

struct SelectionFragment {
  screen_x: Int,
  screen_y: Int,
  cell_width: Int,
  text: Str,
}

struct SelectionResult {
  has_selection: Bool,
  start: Int,
  end: Int,
  fragments: [SelectionFragment],
}
```

A selectable control registers one local hit predicate and one update callback:

```ard
selection_hit: (fn(Int, Int) Bool)?
selection_update: (fn(LocalSelection?) SelectionResult)?
```

`clip` is the paint-equivalent effective clip translated into control-local
coordinates. Fragment coordinates are global, and `cell_width` describes the
complete display span represented by `text`. Read-only controls return only
fragments that survive clipping and never return half of a wide grapheme.
`none` clears local selection. Text converts the internal `start` and `end` to
public `selection::Range`; the runtime consumes only the fragments. Node clears
both callbacks during destruction to break the retained Node/control callback
cycle. The selection runtime revalidates every touched Node before callbacks.

Selection handling takes precedence over ordinary pointer capture:

1. If selectable content accepts a physical left-down cell and Ctrl is not
   held, Cooper starts a new selection before routing the ordinary down event.
   Selection-owned downs do not populate the ordinary pointer `pressed` handle,
   so clearing selection from a callback cannot accidentally arm later pointer
   capture. The down may still autofocus its nearest focusable ancestor.
   Preventing default does not undo the start.
2. Ctrl+left-down with an existing selection extends from the original anchor.
   Like OpenTUI, this gesture is consumed: it does not route an ordinary down,
   start pointer capture, or autofocus.
3. While selection is dragging, physical drag still emits hover transitions,
   updates global focus and local ranges, and then routes drag to the physical
   target with `is_dragging: true`. Ordinary pointer capture is disabled.
4. Each selection drag has a monotonically increasing session generation.
   Physical up routes once to the physical target with `is_dragging: true` and
   finishes only if callbacks have not cleared or replaced that generation. It
   then emits the final snapshot.
5. A normal left down that neither starts nor extends selection routes first,
   then clears the prior selection unless default was prevented.
6. Selection is recomputed after relevant layout or text changes so snapshots,
   painting, and selected text remain consistent.

### Text and editable selection

Selection styling accepts a mutation patch directly over `TextStyle` instead of
introducing a second struct with the same fields:

```ard
ui::text(
  ctx,
  content: "select me",
  selectable: true,
  selection_style: fn(value: mut ui::TextStyle) {
    value.reverse = true
    value.bold = true
  },
)
```

The constructor argument type is `(fn(mut TextStyle))?`. Cooper applies it to an
actual mutable copy and caches the result:

```ard
private fn apply_patch(base: TextStyle, patch: fn(mut TextStyle)) TextStyle {
  let selected = mut base
  patch(selected)
  selected.@
}
```

It reapplies the patch whenever the base TextStyle changes or the setter
replaces the patch. Function values are not comparable, so the setter always
assigns and invalidates. Changes to state captured by a patch closure are not
automatically observable; applications replace the patch to invalidate it.
Omission uses an internal default patch that toggles reverse video; a no-op
closure explicitly preserves the base style. Patch functions must only mutate
their argument and must not retain it. Text becomes selectable by default.

Text adds:

```ard
fn selectable() Bool
fn mut set_selectable(value: Bool)
fn selection() selection::Range?
fn selected_text() Str
fn mut set_selection_style(patch: fn(mut TextStyle))
fn mut on_mouse(handler: fn(mut event::MouseEvent)) fn()
```

The default patch changes only reverse video and otherwise preserves the base
style and terminal-default colors. Text layout retains source grapheme
boundaries, display widths, visual line positions, and explicit newline
offsets. Selection painting overlays complete graphemes and their continuation
cells without splitting wide spans. Changing content, wrap mode, width,
visibility, or destruction recomputes or clears the local selection safely.

Input adds the same `selectable` and `selection_style` constructor options and
these methods:

```ard
fn selectable() Bool
fn mut set_selectable(value: Bool)
fn selection() selection::Range?
fn selected_text() Str
fn mut set_selection_style(patch: fn(mut text::TextStyle))
```

Input stores its editable anchor and focus as UTF-8 byte positions normalized to
grapheme boundaries; those internal positions remain stable while the
single-line viewport pans. Its public `selection::Range` converts them to
display-cell offsets across the complete value. Global-cell mouse positions map
through the current visible-start offset. The focus endpoint drives horizontal
reveal while the anchor remains fixed; dragging beyond the left or right edge
pans by one grapheme per drag event and extends the logical range. Selection
painting clips to the visible viewport, while `selected_text` retains the whole
logical range, including selected content currently panned off-screen.

The existing cursor is the focus end of a collapsed or extended range.
Shift+Left/Right/Home/End extends through the global selection state; movement
without Shift collapses the range toward the movement direction. Backspace,
delete, typing, and paste remove the selected range first and then apply the
existing grapheme and maximum-length rules. Replacement capacity is calculated
after removing the range. `set_value` clears selection and keeps its existing
cursor-at-end contract; reducing `max_length` truncates and clamps or clears the
range. Blur preserves the range but hides the hardware cursor and keeps current
change/submit baseline semantics.

A visible Input contributes its complete logical selected text to global
assembly even when part of that range is internally panned; ancestor clipping
still determines whether the Input participates at all. This selection protocol
is also the basis for future Textarea and rich-text controls.

Read-only Text selection lands before editable Input selection so the global
protocol and grapheme mapping can be validated independently. Interaction is
not considered fully at parity until both are complete.

### Frame ordering

Selection ranges must be current before paint, while user callbacks must not
mutate the tree halfway through a committed frame. Every live and headless frame
therefore has this order:

1. compute layout, reconcile control focus, and apply focus reveal;
2. perform internal selection reconciliation against final geometry and clips;
3. paint the complete logical buffer and commit it to the live terminal or
   TestApp frame;
4. compute and route hover changes against that committed geometry;
5. publish selection-change callbacks queued for that committed generation.

Hover transition targets are determined before any post-commit user callback.
If a hover callback invalidates a queued selection generation, its stale
notification is skipped and the new state is painted before notification.
Internal selection callbacks are framework hooks and cannot invoke application
listeners. Public callbacks and hover listeners run only after commit. Their
mutations schedule another frame; the runtime does not drain or erase those
redraw requests as part of the frame that triggered them. `selection()` returns
the newest internal snapshot even while its public notification is queued.

### Testing contract

TestApp remains backend-independent but uses the exact live interaction state
machine. Its existing low-level `mouse` method remains for physical `down`,
`up`, `move`, `drag`, and `scroll` input only; passing derived `over`, `out`,
`drag_end`, or `drop` kinds panics rather than bypassing state-machine
invariants. Physical entry points reset caller-supplied `is_dragging` to false;
only the selection state machine may set it on routed drag and up events. Live
Vaxis conversion follows the same rule. Before every low-level or convenience
pointer input, TestApp commits an initial or requested frame so hit testing
never observes older geometry than
the equivalent live event path. It does not implicitly execute queued dispatch
actions; callers still use `flush` for those. Deterministic helpers are added:

```ard
fn mouse_move(x: Int, y: Int, modifiers: event::Modifiers?)
fn mouse_down(x: Int, y: Int, button: event::MouseButton?, modifiers: event::Modifiers?)
fn mouse_up(x: Int, y: Int, button: event::MouseButton?, modifiers: event::Modifiers?)
fn click(x: Int, y: Int, button: event::MouseButton?, modifiers: event::Modifiers?)
fn drag(
  start_x: Int,
  start_y: Int,
  end_x: Int,
  end_y: Int,
  button: event::MouseButton?,
  modifiers: event::Modifiers?,
)
```

These helpers send semantic sequences without time delays. `drag` sends down,
one drag at the destination, and up; tests that need intermediate motion use
the lower-level methods.

Headless coverage must include:

- local-coordinate rebinding and bubbling;
- stop/default behavior and structural mutation;
- stable z-index hit order and clipping;
- nearest-ancestor left-button autofocus;
- captured left drag, drop order, and invalidation;
- non-captured right/middle drag;
- hover transitions caused by movement and by layout changes;
- scroll fallback to focused control;
- terminal focus independence;
- control focus/blur listener ordering and reentrancy;
- selection start, extension, session replacement, clear prevention,
  selectable-disable, anchor invalidation, clipping, and reading order;
- wrapped text, explicit newlines, combining graphemes, partially clipped wide
  graphemes, and selection-style composition;
- editable selection replacement, off-screen panning, max-length, blur, and
  cursor behavior;
- post-commit callback ordering and preservation of callback-requested frames;
- identical semantic outcomes through live and headless entry points.

PTY coverage remains responsible for raw Vaxis behavior:

- SGR mouse press, release, motion, drag, and four wheel directions;
- modifiers and zero-based coordinates;
- focus-in and focus-out reports with both `use_mouse: true` and `false`;
- clean restoration with mouse and focus reporting enabled.

Benchmarks add wide sibling overlap, deep hit testing with all controls eligible,
hover reconciliation, and selection across many Text controls. Repeated pointer
movement must not allocate proportional to the full tree when stacking and
layout are unchanged.

### Reference validation program

The end-to-end acceptance fixture is `examples/fixtures/interaction_lab.ard`,
paired with `examples/test_interaction.py`. It is an instrumented UI rather than a second
test framework: every interaction updates a stable visible status field that a
person or PTY test can inspect.

At 100 by 24 cells it presents:

```text
Interaction Lab                         terminal: focused

Focus ancestor     [ nested text inside a focusable card ]
Stacking           [ BACK ][ overlapping FRONT ]
Drag lane          [ SOURCE ] -------------------- [ DROP ZONE ]
Hover layout       [ LEFT ]                        [ RIGHT ]

Selectable text    Alpha élan 你好 — drag across wrapped lines.
                   Second line joins selection in reading order.
Editable input     [ select part of this deliberately long value      ]
Scroll selection   [ nested ScrollBox with selectable numbered rows   ]

focus: none       stack: none       hover: none
 drag: idle        selection: none   last: ready
```

The controls exercise the contract directly:

- the focus card is focusable but its nested Text is the hit control, proving
  nearest-focusable-ancestor autofocus and bubbling;
- BACK and FRONT overlap, use different `z_index` values, and report which one
  receives down;
- SOURCE records drag and drag-end while DROP ZONE records drop, proving
  left-button capture without public source identity;
- pressing `m` swaps the hover tiles beneath a stationary pointer, proving
  post-frame hover reconciliation;
- the read-only text contains wrapping, an explicit newline, a combining
  grapheme, and wide graphemes;
- the Input is wider than its viewport, proving logical selection, horizontal
  reveal, and replacement of a selected range;
- nested ScrollBoxes prove clipped hit translation, wheel fallback, and
  selectable reading order;
- terminal focus reports update the header without changing control focus;
- selection and hover callbacks update status after committed frames, proving
  that callback-requested redraws are preserved.

`test_interaction.py` drives one deterministic scenario:

1. send focus-out and focus-in reports and verify that focused-control state is
   unchanged;
2. click the nested focus label and verify the ancestor focuses;
3. click the overlap and verify FRONT wins;
4. left-drag SOURCE to DROP ZONE and verify source drag-end, one source up,
   target drop, and one target up in order;
5. right-drag across both controls and verify hit-routed drag with no drop;
6. hover LEFT, send `m`, and verify out/over without another mouse sequence;
7. drag-select across wrapped Text, then Ctrl+click to extend it;
8. select a middle Input range and type one grapheme to replace it;
9. wheel the nested ScrollBox and select text after scrolling;
10. exit with Ctrl+C and verify terminal restoration.

Styles and exact cell spans remain headless assertions because the PTY screen
parser observes text, not terminal attributes. The example PTY must pass in
addition to the focused headless matrix before this ADR is considered fully
implemented.

### Module and implementation plan

Public modules remain domain-oriented:

```text
event.ard       routed input and focus values
geometry.ard    Point, Rect, and Geometry
selection.ard   selection snapshots and ranges
text.ard        Text selection mapping and painting
input.ard       editable local selection
```

Unsupported runtime mechanisms are:

```text
core/pointer.ard          shared pointer state machine
core/selection_state.ard  global selection orchestration
core/focus.ard            single-control focus and reveal
core/hit.ard              clipped, stacking-aware hit traversal
core/router.ard           mutation-safe bubbling
core/app_runtime.ard      Vaxis conversion, scheduling, and delegation
```

The dependency direction is:

```text
event
selection -> geometry
core/node -> event, geometry
core/hit -> core/node
core/focus -> core/node, event
core/router -> core/node, event, core/focus
core/selection_state -> core/node, event, selection
core/pointer -> core/node, event, core/hit, core/router,
                core/focus, core/selection_state
core/app_runtime -> core/pointer, core/selection_state, core/focus
```

Public `selection.ard` never imports Node. `core/pointer` and
`core/selection_state` never import App or Root. Selection state owns its
root-scoped anchor shape rather than importing pointer. `core/app_runtime`
remains independent of `root.ard`.

Ard public structs expose their field types recursively. Therefore
`pointer::State`, `pointer::AttachmentHandle`, `selection_state::State`, the
selection anchor type, Node's selection protocol structs, and any
pending-notification entry stored in those
states remain language-public. Their `core/` paths communicate the unsupported
boundary; they must not be marked private while a public State or callback field
names them.

Implementation proceeds in reviewable phases:

1. Add mouse drag state, make hit participation uniform, and add z-index without
   changing capture behavior.
2. Extract the shared pointer state machine and align capture, hover, scroll,
   default, and autofocus semantics for live and TestApp.
3. Add the terminal-focus API.
4. Add public selection values, Node selection hooks, global selection state,
   and selectable Text.
5. Add editable Input selection and selection-aware editing.
6. Add PTY coverage, the Interaction Lab, performance benchmarks, examples, and
   final documentation; then verify the complete implementation against this
   accepted ADR.

Each phase must keep formatter checks, all Ard tests, Go tests, existing PTY
suites, and benchmark smoke passing. No compatibility aliases are retained for
changed event fields or semantics.

## Consequences

- Cooper gains one coherent interaction model shared by live and headless
  runtimes.
- Mouse behavior becomes predictable under overlap, clipping, reparenting,
  destruction, drag capture, and layout changes.
- Applications can observe terminal focus and selection without depending on
  unsupported Node values; focused-control observation stays local to controls.
- Text selection requires richer grapheme-to-visual-cell layout data and makes
  text measurement, painting, and selection share one representation.
- Input selection materially expands editing state and must preserve existing
  change, submit, max-length, and grapheme invariants.
- All controls becoming hit targets increases hit-test work; stacking caches and
  benchmarks become required safeguards.
- `z_index`, terminal focus, and selection expand the public API.
- Mouse `prevent_default` changes behavior: it no longer suppresses built-in
  control mouse handling. This supersedes that part of ADR 0002.
- Uniform hit participation supersedes ADR 0002's listener-gated Box hit
  participation.
- Stable `z_index` paint and hit order supersedes ADR 0002's rule that child
  order alone controls drawing and hit testing; child order remains the
  equal-z-index tie-breaker.
- Text becomes selectable by default, superseding ADR 0002's deferred selection
  decision.
- Cooper remains intentionally different from OpenTUI in listener convenience,
  hit-test implementation, and backend-independent TestApp input.

## Related

- [ADR 0002: Define the Application API](./0002-define-application-api.md)
- [OpenTUI: Interaction, focus, and selection](https://opentui.com/docs/core-concepts/interaction/)
- [OpenTUI `MouseEvent` and pointer processing](https://github.com/anomalyco/opentui/blob/eaf1d41e9252505232b1cbeae3ab05c15a55243d/packages/core/src/renderer.ts)
- [OpenTUI selection model](https://github.com/anomalyco/opentui/blob/eaf1d41e9252505232b1cbeae3ab05c15a55243d/packages/core/src/lib/selection.ts)
- [OpenTUI mock mouse](https://github.com/anomalyco/opentui/blob/eaf1d41e9252505232b1cbeae3ab05c15a55243d/packages/core/src/testing/mock-mouse.ts)
- [Vaxis events](https://pkg.go.dev/go.rockorager.dev/vaxis#FocusIn)
