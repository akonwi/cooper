# 0011: Define the Multiline TextArea

## Status

Accepted. Package paths and module placement are superseded by
[ADR 0015](./0015-define-package-entry-points-and-ui-namespace.md).

## Context

Cooper's `Input` provides grapheme-safe single-line editing, editable selection,
callbacks, and horizontal cursor reveal. The Ard-native editor model extracted
in ADR 0004 deliberately kept multiline visual movement out of that control.
Real applications now need editable comments, descriptions, and other text that
contains hard line breaks and wraps inside a bounded viewport.

A multiline editor cannot be composed safely from a selectable Text inside a
ScrollBox. Keyboard focus belongs to one retained Node, editable selection must
map source byte boundaries to visual cells, and the cursor and internal viewport
must settle from one frame-consistent layout. TextArea therefore needs to be a
first-class retained control while continuing to reuse `editor::State` for
logical edits.

## Decision

### Public control

Add `text_area.ard` with one persistent `TextArea` control:

```ard
text_area::new(
  ctx,
  value: "",
  placeholder: "Write a comment…",
  wrap: text::TextWrap::word,
  styles: style::new(
    min_width: style::cells(60),
    min_height: style::cells(6),
  ),
  text_style: text::style(),
  placeholder_style: text::style(dim: true),
  selectable: true,
  selection_style: fn(value: mut text::TextStyle) {
    value.reverse = true
  },
  scrollbar_options: scrollbar::options(
    visibility: scrollbar::Visibility::automatic,
  ),
)
```

The constructor returns an infallible mutable retained control. Common Style
owns width, height, minimums, maximums, colors, visibility, and placement; the
TextArea does not duplicate those fields.

TextArea exposes:

```ard
fn value() Str
fn mut set_value(value: Str)
fn placeholder() Str
fn mut set_placeholder(value: Str)
fn wrap() text::TextWrap
fn mut set_wrap(value: text::TextWrap)

fn text_style() text::TextStyle
fn mut set_text_style(value: text::TextStyle)
fn placeholder_style() text::TextStyle
fn mut set_placeholder_style(value: text::TextStyle)

fn selectable() Bool
fn mut set_selectable(value: Bool)
fn selection() selection::Range?
fn selected_text() Str
fn mut set_selection_style(patch: fn(mut text::TextStyle))

fn scrollbar_options() scrollbar::Options
fn mut set_scrollbar_options(value: scrollbar::Options)

fn mut focus() Bool
fn mut blur()
fn is_focused() Bool
fn mut on_key(handler: fn(mut event::KeyEvent)) fn()
fn mut on_paste(handler: fn(mut event::PasteEvent)) fn()
fn mut on_mouse(handler: fn(mut event::MouseEvent)) fn()
fn mut on_focus(handler: fn()) fn()
fn mut on_blur(handler: fn()) fn()
fn mut on_input(handler: fn(Str)) fn()

fn style() style::Style
fn mut set_style(value: style::Style)
fn layout() geometry::Geometry
fn mut destroy(recursive: Bool?)
```

`ui` re-exports `TextArea` and `ui::text_area`.

TextArea intentionally has no minimum/maximum length, commit baseline,
`on_change`, `submit`, or `on_submit`. Those remain Input-specific validation
and form-commit behavior. Applications submit multiline values through their
own key listener or command router.

### Source and callback behavior

Values preserve tabs and line feeds. Constructor values, `set_value`, typed
text, and paste normalize CRLF and bare CR to LF. Plain Return inserts one LF.
One typed insertion, deletion, selected replacement, or paste emits exactly one
`on_input` callback when text changes.

Live bracketed paste is aggregated application-wide between Vaxis paste-start
and paste-end reports before App or control paste listeners run. Printable text,
line feeds, and tabs are preserved; terminal control sequences unsupported by
Vaxis's parsed Key representation do not become editable text. The backend uses
a reusable linear buffer and clears an incomplete paste on restart, suspension,
or teardown. Input and TextArea therefore both observe one callback transaction
for one terminal paste, matching headless `PasteEvent` delivery.

`set_value` moves the cursor to the end, clears editable and global selection,
resets the internal viewport, and emits input only when the normalized value
changes. Listener removal remains idempotent through Node's common listener
contract.

User key and paste listeners run before built-in behavior. `prevent_default`
therefore lets an application reserve commands such as Ctrl+Enter without
inserting text. Cooper does not add a TextArea-specific submit chord.

### Layout and viewport

TextArea uses a source-preserving Ard layout model. Every grapheme records its
UTF-8 source range, flattened display-cell range, terminal width, and visual
position. Hard newlines consume one logical selection offset but are not painted
as source glyphs. Empty and trailing lines retain caret positions.

`TextWrap::word` is the default. Character and word wrapping never split a
complete grapheme. `TextWrap::none` retains hard lines and enables horizontal
panning. Intrinsic measurement uses unwrapped line widths; finite width
constraints use the configured wrap mode.

When content exceeds final layout height, TextArea scrolls internally. Cursor
actions reveal the caret vertically and, in no-wrap mode, horizontally. Wheel
input moves the internal viewport and bubbles to ancestor ScrollBoxes only when
the requested axis cannot move. Manual wheel scrolling may temporarily hide the
caret and is not undone by unrelated frames.

TextArea composes the existing vertical `Scrollbar` primitive and defaults to
`Visibility::automatic`. The bar paints only for vertical overflow, reserves a
stable one-cell gutter, reflects cursor/wheel scrolling, and supports the same
track presses, thumb dragging, arrows, visibility, and Appearance overrides as
a ScrollBox bar. `scrollbar_options` and `set_scrollbar_options` can select
`always` or `hidden` behavior and configure its presentation. The private bar
is not a separate focus-traversal stop.

TextArea clips its own content independently of common Style overflow. A control
must never paint editable rows over a sibling merely because its public Style
uses visible overflow.

Focus reveal uses a private Node reveal-bounds resolver. Ordinary controls
continue to reveal their complete bounds; TextArea reveals its current cursor
cell through ancestor ScrollBoxes. This resolver is unsupported runtime
machinery and does not expose cursor Nodes or geometry publicly.

### Editing profile

TextArea reuses editor actions for grapheme and word movement, selection,
deletions, and the deferred undo/redo chords. It adds visual behavior at the
control adapter:

- Up/Down move by visual rows and preserve a preferred display column;
- Page Up/Down move by the visible viewport height;
- Home/End, Ctrl+A/Ctrl+E, and Super+Left/Right move to hard-line boundaries;
- shifted variants extend selection;
- Super+A selects the complete buffer;
- Ctrl+U/Ctrl+K delete to the current hard-line boundary;
- Return inserts a newline;
- printable unmodified text and terminal paste insert source text.

Release events are ignored. Press and repeat execute the same action. Unsupported
modified text is ignored instead of becoming content. Tab remains ordinary text
when a terminal reports it as printable; application focus traversal is explicit
and can reserve it in an App listener.

Undo and redo retain ADR 0004's current handled no-op behavior until editor
history is implemented.

### Selection

TextArea stores editable anchor and cursor positions as UTF-8 byte boundaries in
`editor::State`. Public `selection::Range` uses flattened display cells; hard
newlines count as one, while soft wraps add no source offset. `selected_text`
preserves source newlines and tabs.

Keyboard and mouse selection use Cooper's one global selection runtime. Internal
scrolling and reflow do not change the selected source range. When any part of a
selected TextArea intersects its effective ancestor clip, it contributes its
complete editable source as one atomic selection fragment. A fully clipped
TextArea contributes no copied text. This preserves offscreen editable content
without replacing fragments from neighboring controls in a cross-control
selection.

Selected visible graphemes use the configured selection style. A selected hard
newline paints one blank marker cell when its line-end cell fits, including the
first cell of an empty selected line. Wide graphemes are painted and selected
only as complete spans.

Pointer edge dragging scrolls at most one visual row or column per physical drag
update and extends selection through the newly visible edge. Layout-only frames
do not add another pan step. Editable double-click word selection and
triple-click line selection remain deferred.

### Internal module boundary

`text_area_layout.ard` is root-level supporting logic for the public TextArea
domain. It is language-visible because Ard declarations used across modules are
public, but it is not a separately supported application control API.

`core/node.ard` gains only the optional focus-reveal resolver used by focus
orchestration. Vaxis remains limited to terminal grapheme measurement and final
cell output.

## Consequences

- Cooper can support multiline forms without applications importing `core/` or
  embedding Vaxis/ui widgets.
- TextArea and Input share logical editor actions while retaining distinct
  single-line commit and multiline viewport semantics.
- Source-aware wrapping, cursor mapping, internal scrolling, editable
  selection, and built-in Scrollbar interaction add substantial deterministic
  test surface.
- Layout currently rebuilds grapheme mappings from immutable Ard strings. A
  rope, indexed cache, history, syntax state, and public scroll metrics remain
  deferred until long-document benchmarks demonstrate a need.
- Applications remain responsible for form submission, focus traversal, and
  mode-aware shortcut routing.

## Related

- [ADR 0002: Define the Application API](./0002-define-application-api.md)
- [ADR 0003: Define Interaction, Focus, and Selection](./0003-define-interaction-focus-and-selection.md)
- [ADR 0004: Define Input Editor State and CLI Keybindings](./0004-define-input-editor-and-keybindings.md)
- [ADR 0005: Define Rich Text, Wrapping, and Multi-Click Selection](./0005-define-rich-text-wrapping-and-multi-click-selection.md)
