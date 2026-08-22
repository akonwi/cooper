# 0005: Define Rich Text, Wrapping, and Multi-Click Selection

## Status

Accepted

## Context

Cooper's `Text` is already a capable Ard-native plain-text control. It owns
mutable content, terminal-default and inherited colors, explicit text styles,
none/character/word wrapping, Unicode grapheme-safe painting, terminal-cell
measurement, retained layout, and read-only selection. Its selection style can
patch every supported text attribute rather than only foreground and
background.

OpenTUI's Text provides the same plain-text base but supports additional content
and viewport behavior through `StyledText`, inline Text nodes, hyperlinks,
hidden text, Unicode-aware word wrapping, ellipsis truncation, tab indicators,
internal scrolling, and line/scroll metrics. Its current implementation accepts
either a string or styled chunks and delegates hot layout to a native text
buffer. React and Solid additionally compose inline text-only children.

Cooper should adopt rich inline content and the observable text behaviors that
are useful to Ard applications without copying OpenTUI's retained Text-node
subtree, native rope, or internal scrolling. Plain strings must remain the
simple path. Framework text semantics, style resolution, wrapping, selection,
and source mapping remain Ard-owned.

Cooper currently begins read-only selection only when a left press lands on a
rendered grapheme. This narrower start region is acceptable and remains
unchanged. However, native-feeling read-only selection also requires an
unmodified double left-click on text to select the complete word-like run under
the pointer. Vaxis/ui provides this behavior by recognizing repeated presses in
the selection area and asking the selected text object for a word range.

## Decision

### One Text control with plain and styled content

Keep one retained `Text` control. Do not add a distinct `RichText` control.
Internally, Text always operates on a flattened styled content stream. Plain
content is represented as one unstyled span.

Add Ard-native snapshot value data with this conceptual shape:

```ard
struct SpanStyle {
  foreground: color::Color?,
  background: color::Color?,
  bold: Bool?,
  dim: Bool?,
  italic: Bool?,
  underline: Bool?,
  blink: Bool?,
  reverse: Bool?,
  strike: Bool?,
  hidden: Bool?,
}

struct Span {
  text: Str,
  style: SpanStyle,
  link: Str?,
}

struct StyledText {
  spans: [Span],
}

fn span_style(
  foreground: color::Color?,
  background: color::Color?,
  bold: Bool?,
  dim: Bool?,
  italic: Bool?,
  underline: Bool?,
  blink: Bool?,
  reverse: Bool?,
  strike: Bool?,
  hidden: Bool?,
) SpanStyle
fn span(text: Str, style: SpanStyle?, link: Str?) Span
fn styled_text(spans: [Span]) StyledText
```

Provide `span_style`, `span`, and `styled_text` helper constructors so plain
spans do not require verbose struct literals. Public structs remain directly
constructible. An omitted SpanStyle field inherits the Text-level `TextStyle`;
an explicitly configured Bool overrides the inherited attribute. An omitted
span color inherits. Explicitly clearing one span color back to the terminal default
is deferred until Cooper has a general tri-state color value.

The `styled_text` helper, every Text ingress, and `styled_content()` create
defensive span-list snapshots so later mutation of a caller-owned list cannot
mutate retained content. A directly constructed StyledText may still share its
caller-owned list until passed into Text. `styled_content()` preserves empty
spans, original style boundaries, and links exactly. Implementations compare
spans explicitly or invalidate unconditionally; list identity and whole-value
equality are not content equality.

Add `hidden` to the shared TextStyle. Hidden content retains its source length,
display width, wrapping, cursor, and selection mapping while requesting the
terminal's invisible text attribute. It applies consistently to Text, Input
values, Input placeholders, and selection overlays. Existing default selection
patches preserve hidden; an application patch may explicitly reveal selected
content. Append the optional `hidden` argument to the existing `text::style`
helper so positional calls retain their current meaning.

Use Ard's named union to keep one constructor and preserve plain-string
ergonomics:

```ard
type TextContent = Str | StyledText

fn new(
  ctx: mut context::Context,
  content: TextContent,
  wrap: TextWrap?,
  styles: layout_style::Style?,
  text_style: TextStyle?,
  selectable: Bool?,
  selection_style: (fn(mut TextStyle))?,
  overflow: TextOverflow?,
) mut Text
```

The overflow option is appended after existing constructor options so
positional calls retain their current meaning. Existing `content: "plain"`
calls remain valid. Text exposes:

```ard
fn content() Str
fn styled_content() StyledText
fn mut set_content(content: TextContent)
fn overflow() TextOverflow
fn mut set_overflow(overflow: TextOverflow)
```

`content()` always returns flattened plain source text. Passing a Str to
`set_content` replaces the styled stream with one unstyled span; passing a
StyledText preserves its supplied span boundaries. Empty spans are permitted
but contribute no geometry or selection fragment. The existing `content`
parameter label is retained for named method calls.

`ui` re-exports TextContent, StyledText, Span, SpanStyle, and TextOverflow, plus
`ui.span_style`, `ui.span`, and `ui.styled_text`, alongside `ui.text`. The
existing `ui.text_style` alias remains the shared TextStyle helper. Callers do
not need a second module import for rich content.

Styled spans are value content, not retained children. They cannot receive
focus, pointer events, layout, or lifecycle callbacks. Style boundaries do not
create grapheme, word, wrap, or selection boundaries.

### Style-aware text layout

Replace the current string-only layout pipeline with an Ard-native flattened
glyph stream. Each logical glyph retains:

- its grapheme text and terminal-cell width;
- source UTF-8 byte and display-cell offsets in flattened content;
- its resolved TextStyle and optional hyperlink;
- explicit newline information;
- its visual x/y position after wrapping.

Grapheme segmentation occurs across span boundaries. Splitting a combining or
emoji sequence across adjacent spans must not produce two painted graphemes.
When one grapheme contains multiple spans, the resolved style and hyperlink of
its first scalar win for the complete terminal grapheme; this deterministic
rule avoids splitting one terminal cell span. Selection styling applies ADR
0003's configured patch independently to each glyph's resolved style and
preserves that glyph's resolved hyperlink.

Adjacent visual glyphs with the same resolved style and link may be painted as
one run. This is an optimization only and does not change public content or
selection offsets.

Plain Text retains terminal-default colors and common Style inheritance.
Cooper does not adopt OpenTUI's default white foreground.

### Unicode-aware wrapping

Retain the existing public modes:

```ard
enum TextWrap {
  none,
  character,
  word,
}
```

Change Text's default from `none` to `word` while Cooper has no compatibility
constraint. `none` remains available for status lines and explicitly clipped
single-line content. An undefined measurement width always computes intrinsic
unwrapped width and explicit-line height; wrapping occurs only under a finite
width constraint. The new default must not collapse intrinsically measured Text
to one-cell lines.

Character wrapping breaks only between complete graphemes. Word wrapping uses
Unicode line-break properties from the existing Unicode boundary dependency
and an Ard-owned policy. The initial observable contract is:

- preserve explicit newlines and empty lines;
- preserve ordinary words when they fit;
- break at whitespace, punctuation, hyphens, and script-appropriate CJK
  opportunities;
- handle mixed CJK, emoji, and Latin content without splitting Latin words;
- fall back to grapheme wrapping for an otherwise unbreakable run wider than
  the available width;
- never split a grapheme or discard source content;
- wrap seamlessly across style boundaries.

Complete UAX #14 conformance is not required for the first implementation. The
supported policy is established by deterministic Unicode fixtures and can be
extended without changing the public modes.

### Text overflow and ellipsis

Text does not gain internal scrolling. Applications continue to compose Text
inside `ScrollBox`; horizontal scrolling remains deferred until Cooper has a
reusable horizontal viewport primitive.

Add a text-specific overflow policy separate from layout Style's descendant
clipping:

```ard
enum TextOverflow {
  clip,
  ellipsis,
}
```

The constructor's `overflow` option defaults to `clip`; `overflow()` and
`set_overflow()` inspect and mutate it. A changed policy requests measurement
and paint reconciliation because ellipsis can alter the last visual line.

`clip` preserves current painting. `ellipsis` applies only
when the laid-out content exceeds a finite Text width or height. It paints one
Unicode ellipsis in the last fitting cell range and never paints a partial wide
grapheme. Widths that cannot fit an ellipsis paint no partial marker. The
ellipsis uses the resolved style immediately before the omitted source, or the
Text-level style when no source glyph fits, and carries no hyperlink.

The ellipsis is synthetic and is not selectable. A press or drag endpoint on
its cell clamps to the preceding visible source boundary. Source glyphs omitted
by active ellipsis truncation do not contribute to local or global selected
text, even when a cross-control selection spans the Text; copying reflects the
visible terminal content. The ellipsis itself never appears in `content`,
`selected_text`, or source ranges. If layout later exposes more content,
selection reconciliation uses the newly visible source glyphs.

Tab indicators, public line counts, virtual-line counts, and scroll metrics are
deferred. Cooper continues to expand tabs using its terminal width measurer and
preserve original tab characters in local selected text.

### Hyperlinks

A non-empty Span link emits OSC 8 hyperlink metadata for all complete cells of
that span. Hyperlinks remain Ard-owned value data and are converted to Vaxis
style fields only by the paint/backend boundary. Continuation cells carry the
same link metadata. Links are terminal annotations, not interactive controls;
Cooper does not add focus, activation callbacks, URL parsing, or pointer cursor
policy to Text spans.

Every StyledText ingress validates links before storing or painting them,
including directly constructed Span values. A link containing any C0 or C1
control character, DEL, ESC, BEL, or string-terminator sequence is a programmer
contract violation and panics. Cooper never forwards untrusted terminal control
bytes into Vaxis's OSC 8 fields. Other Unicode text and URI schemes remain
unparsed value data.

The backend-independent CellStyle, TestApp cells, equality, clearing, and wide
span invalidation must preserve and clear hyperlink data deterministically.
Hyperlink parameters are deferred.

### Read-only double-click word selection

Keep the current single-click selection start rule: a left press without Ctrl
must land on a rendered selectable grapheme. Shift, Alt, or Super do not prevent
an ordinary single-click selection start. A drag continues to use Cooper's
global cross-control selection state.

Only presses with no modifiers participate in double-click recognition. Two
unmodified left-button presses form a double-click when they:

- occur no more than 500 milliseconds apart;
- use the same screen cell;
- target the same live selectable Text attachment;
- retain the same collapsed selection generation started by the first press;
- are not separated by a modified press, different button, Ctrl-extension,
  drag, target invalidation, or application teardown.

The second press replaces the collapsed first selection with the complete
word-like run containing the pointed grapheme and immediately finalizes the
selection. Its following release does not collapse the selected run. Dragging
by word after the second press is deferred.

Multi-click recognition belongs to the retained pointer/global-selection
layer, not `MouseEvent` or Text's public listener API. The pointer state uses a
monotonic clock seam so TestApp can advance time deterministically.

The pointer click candidate stores the first collapsed session generation. If
an `on_selection_change` callback clears or replaces that session before the
second press, generation comparison rejects double-click expansion even when
time and coordinates still match.

The internal Node selection adapter adds expansion and resolution callbacks.
Expansion maps a local point and `word` granularity to an end-exclusive logical
display-cell range, its visual local anchor/focus endpoints, and the Text
source-mapping revision. The active selection session stores that range.
Resolution maps the same range back to visual endpoints after movement, resize,
or reflow, so a wrapped word selection remains source-anchored rather than
selecting new cells at stale coordinates.

The source-mapping revision changes only when flattened source text or its
grapheme/display-offset mapping changes. Span boundaries, links, colors, and
other presentation-only changes do not invalidate a word selection. A mapping
revision mismatch invalidates the locked range and safely clears it instead of
applying stale offsets.

The runtime continues to publish screen-cell anchor, focus, and bounds through
ADR 0003. Expansion occurs before the second mouse-down is delivered, matching
current selection-start ordering. After listener delivery, the session is kept only if its generation still
matches the click candidate and its Text attachment is current; reentrant
clear, content replacement, reparent, hiding, or destruction cannot resurrect
the word selection. This adapter shape is reusable by rich Text because word
boundaries operate on flattened plain content.

Word selection is grapheme-safe and classifies runs as follows:

1. Unicode letters, numbers, marks, and connector punctuation form word runs;
2. Unicode whitespace forms whitespace runs;
3. punctuation and symbols form non-word runs;
4. internal apostrophes between word glyphs join the surrounding word;
5. style boundaries do not end a run;
6. a run may cross visual wrapped lines but never an explicit newline.

Double-clicking punctuation or whitespace selects its contiguous run, matching
the same deterministic run model used by editor word actions. Selection
painting and `selected_text` preserve original source text and per-span styles.

Triple-click line selection, Ctrl+A/C selection-area shortcuts, and editable
Input multi-click selection are deferred. Ctrl+click retains ADR 0003's global
selection extension behavior and does not participate in double-click counting.

### Code and Markdown remain separate

Text does not parse ANSI, Markdown, syntax markup, or HTML-like inline tags.
Future Code and Markdown controls may produce StyledText values and reuse the
same glyph layout and paint pipeline. Parsing and syntax-state APIs remain out
of scope for Text.

### Implementation order

1. Characterize current plain layout, selection, clipping, tabs, and content
   mutation behavior.
2. Add double-click recognition and pure Text word-range mapping without
   changing single-click or drag selection.
3. Introduce StyledText/Span values and migrate plain Text to the flattened
   style-aware glyph pipeline without observable plain-text regressions.
4. Widen the constructor and setter to TextContent, add helper constructors and
   UI aliases, then add style inheritance, hidden text, snapshot, ingress
   validation, and cross-span grapheme tests.
5. Replace whitespace-only word wrapping with the documented Unicode policy and
   change the default to word.
6. Add backend-independent hyperlink metadata and OSC 8 conversion.
7. Add ellipsis overflow and selection behavior around omitted content.
8. Reassess caching or a rope only after long-content benchmarks show a need.

Pure span, grapheme, word-run, and wrapping unit tests live beside their subject
in `text.ard`. Retained layout, global selection, pointer timing, clipping,
backend conversion, and PTY tests remain in the integration suites. TestApp
provides a deterministic double-click helper; tests do not sleep against the
500 millisecond threshold.

## Consequences

- Cooper gains the principal missing OpenTUI Text capability: multiple inline
  styles in one retained Text control.
- Plain strings remain ergonomic and continue to use terminal-default and
  inherited colors.
- Rich content, wrapping, selection, links, and future Code/Markdown controls
  share one Ard-owned source-to-visual mapping.
- Switching the default wrap mode can change constrained Text layout, which is
  intentional before compatibility is promised.
- Unicode wrapping and cross-span graphemes materially increase layout
  complexity and require broader fixtures.
- Ard's named union preserves one Text constructor and accepts existing plain
  strings without creating a second retained control.
- Double-click timing introduces small retained pointer state and a deterministic
  clock seam for TestApp.
- Hyperlinks require backend-independent cell metadata but no new public event
  behavior.
- Text remains a content control rather than becoming a scroll viewport or
  retained subtree.

## Related

- [ADR 0002: Define Application API](./0002-define-application-api.md)
- [ADR 0003: Define Interaction, Focus, and Selection](./0003-define-interaction-focus-and-selection.md)
- [ADR 0004: Define Input Editor State and CLI Keybindings](./0004-define-input-editor-and-keybindings.md)
- [OpenTUI Text](https://opentui.com/docs/components/text/)
- [OpenTUI TextRenderable](https://github.com/anomalyco/opentui/blob/main/packages/core/src/renderables/Text.ts)
- [OpenTUI TextBufferRenderable](https://github.com/anomalyco/opentui/blob/main/packages/core/src/renderables/TextBufferRenderable.ts)
- [Vaxis/ui SelectionArea](https://github.com/rockorager/vaxis/blob/main/ui/selection_area.go)
- [Ard issue 459: nullable module-qualified struct literal lowering](https://github.com/akonwi/ard/issues/459)
