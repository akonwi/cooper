# Cooper examples

These applications exercise Cooper's accepted application API and require Ard
v0.38.0 or newer.

Every example uses `App.context`, the permanent `App.root`, persistent public
controls, and explicit focus policy. Most use blocking `run()`; the lifecycle
example demonstrates nonblocking startup.

## Quickstart

`quickstart.ard` recreates OpenTUI's imperative quickstart with nested styled
Boxes, inherited colors, mutable Text, application key listeners, and the
single-import `cooper/ui` control aliases.

```sh
ard run quickstart.ard
```

Use Left and Right to change the counter, or press Q to quit.

## Layout playground

`layout_playground.ard` keeps four colored cards mounted while seven keyboard-
selectable presets replace their complete Styles. It demonstrates horizontal and
vertical flow, wrapping, grow and shrink, alignment, space distribution,
row reversal, absolute positioning, clipping, z-index, and automatic reflow when
the terminal is resized.

```sh
ard run layout_playground.ard
```

Press 1–7 to choose a preset, Space to advance, or Q to quit.

## Text gallery

`text_gallery.ard` is a selectable specimen sheet for rich spans, terminal text
attributes, foreground and background colors, Unicode graphemes, links, wrapping,
and overflow. Three retained Text controls render the same replaceable sample
with word, character, and no wrapping.

```sh
ard run text_gallery.ard
```

Press 1–3 to choose text samples, Space to advance, E to toggle clipping and
ellipsis, C to clear the selection, or Q to quit. Drag or double-click text to
inspect the logical selection; link activation is intercepted by the gallery.

## Operations dashboard

`dashboard.ard` is a live synthetic operations console built entirely from
persistent Box, Text, and ScrollBox controls. A cancellation-aware background
fiber posts periodic metric, sparkline, status, and bounded event-stream updates
through `Context.dispatch`. The log follows new rows until the operator scrolls
or disables follow mode.

```sh
ard run dashboard.ard
```

Press Space to pause, F to toggle log following, A to insert a manual alert, C
to clear the event stream, or Q to quit. Arrow and paging keys scroll the focused
log; End restores follow mode.

## Stacking contexts

`stacking.ard` adapts OpenTUI's nested z-index and relative-positioning demos.
Three overlapping parent groups each own a shadow, panel, and `z=99` child badge;
the badge cannot escape its parent's sibling stacking order. Raising or moving a
parent updates the complete retained subtree, including paint and hit-test order.

```sh
ard run stacking.ard
```

Press 1–3 or Space to raise a layer, use arrows or H/J/K/L to move it, A to
toggle dispatched autoplay, R to reset the scene, or Q to quit. Exposed card
edges can also be clicked to raise their complete group.

## Input lab

`input_lab.ard` presents four retained single-line Inputs for minimum/maximum
lengths, app-owned email shape validation, Unicode grapheme limits, custom
selection styling, and editing with global selection disabled. Live diagnostics
separate input, change, submit, rejected submit, selection, and terminal paste
activity. The scrolling field panel reveals focused controls in compact windows.

```sh
ard run input_lab.ard
```

Press Tab or Shift+Tab to traverse, Return to submit, or Escape to clear the
selection. Mouse presses place the cursor and drags select text. Terminal paste
is normalized and still respects maximum length; the lab deliberately does not
claim unsupported clipboard, password, or multiline APIs. Press Ctrl+C to quit.

## Mouse interaction demo

`event_inspector.ard` closely adapts OpenTUI's `mouse-interaction-demo.ts` with
Cooper's retained public controls. Four overlapping colored boxes can be raised,
dragged, scrolled, and dropped onto each other. Pointer movement leaves cyan
trail markers, captured drags leave orange markers, and empty-cell clicks toggle
a pink activation layer. The fourth box deliberately clips an oversized child.

```sh
ard run event_inspector.ard
```

Move and drag the pointer around the stage, click empty cells, or scroll over a
box. Press C to clear trail/activation markers, R to restore card positions, or
Ctrl+C to quit. Cooper uses opaque terminal colors and retained Text markers in
place of OpenTUI's alpha-blended framebuffer, fading trails, and timeline bounce,
but preserves the demo's primary interactive behaviors and visual organization.

## Interactive links

`links.ard` closely adapts OpenTUI's `link-demo.ts`: the same absolute header and
three colored project, documentation, and connection cards contain styled OSC 8
links. Cooper's destinations replace OpenTUI's, and opaque colors replace alpha
compositing. The header reports Cooper link activation directly.

```sh
ard run links.ard
```

With drag mode off, plain-click a link to open it with the host handler. Press D
to enable card dragging; cards preserve the pointer offset, clamp to terminal
bounds, and rise above siblings. Plain link activation is suppressed while drag
mode is on so grabbing linked text cannot launch a browser accidentally. Press D
again to restore link activation, or Ctrl+C to quit.

## Focus restore demo

`terminal_focus.ard` closely adapts OpenTUI's `focus-restore-demo.ts`. Its live
terminal-state panel tracks focus state, pointer coordinates, focus-in/out
counts, timestamps, and the first mouse event after each focus return. A bounded,
followed event log keeps the latest 20 focus and tracking-resume observations.

```sh
ard run terminal_focus.ard
```

Move the pointer, alt-tab away and back, then move it again. A `MOUSE RESUMED`
entry confirms the observable outcome without reaching through Cooper's public
API to count private backend mode-restoration calls. Terminals without DEC focus
reporting leave the state `UNKNOWN`. Press Ctrl+C to quit.

## Widget lab

`widgets.ard` combines close app-local adaptations of OpenTUI's
`tab-select-demo.ts`, `select-demo.ts`, and `slider-demo.ts`. F1 presents a
12-option horizontally scrolling TabSelect with separate highlight and
activation state. F2 presents a 20-option Select with descriptions, fast
scrolling, reveal, wrapping, and an indicator. F3 presents three horizontal and
four vertical sliders with different ranges, dimensions, mouse dragging,
keyboard adjustment, reset, and two animated specimens.

```sh
ard run widgets.ard
```

Use F1–F3 or click the header controls to switch pages. Each page lists its own
keys; slider numbers 1–7 focus individual sliders. The controls are intentionally
composed only from persistent public Box, Text, and ScrollBox controls rather
than presented as built-ins. Their behavior is the functional-parity fixture for
future built-in Select and TabSelect APIs. Cooper uses Unicode block cells in
place of OpenTUI's sub-cell slider renderer. Press Ctrl+C to quit.

## Filesystem explorer

`explorer.ard` asynchronously reads the current working directory and creates
persistent public Box and Text controls through UI dispatch. Tab focuses the
first row, Enter and mouse presses activate rows, and the listing ScrollBox
handles wheel input.

```sh
ard run explorer.ard
```

## Test fixtures

Focused lifecycle and regression programs live in [`fixtures/`](./fixtures/)
rather than the public gallery. They preserve targeted ScrollBox, asynchronous
cancellation, application lifecycle, terminal focus, and end-to-end interaction
coverage without presenting overlapping showcase applications.

## PTY smoke tests

The harness builds generated executables in the repository-level `ard-out/`
directory.

```sh
python3 test_layout_playground.py
python3 test_text_gallery.py
python3 test_dashboard.py
python3 test_stacking.py
python3 test_input_lab.py
python3 test_event_inspector.py
python3 test_links.py
python3 test_terminal_focus.py
python3 test_widgets.py
python3 test_scroll_form.py
python3 test_async.py
python3 test_lifecycle.py
python3 test_explorer.py
python3 test_interaction.py
```

The tests cover terminal startup/restoration, retained layout reconfiguration,
rich text, wrapping, overflow, links, selection, live dispatched metrics,
bounded follow-mode logs, nested stacking and hit order, Input validation and
commit callbacks, paste limits, draggable z-index objects, pointer trails,
activated cells, drag/drop routing, interactive links, link-safe drag mode,
terminal focus transitions, post-focus mouse resumption, app-local TabSelect,
Select, and slider behavior, overflow clipping, editing, explicit focus policy,
mouse input, scrolling, resize, App
cancellation, asynchronous UI dispatch, nonblocking startup,
suspension/resume, filesystem rows, drag capture/drop ordering, hover
reconciliation, terminal focus, text and editable selection, and clean exit.
