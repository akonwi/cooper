# 0004: Define Input Editor State and CLI Keybindings

## Status

Accepted. Package paths and module placement are superseded by
[ADR 0015](./0015-define-package-entry-points-and-ui-namespace.md).

## Context

Cooper's `Input` already provides grapheme-safe single-line editing, horizontal
cursor reveal, editable selection, validation, and input/change/submit
callbacks. Its behavior is correct, but `input.ard` currently owns the logical
text model, terminal-cell mapping, global selection adapter, rendering, Node
lifecycle, and a growing conditional key handler in one module.

OpenTUI separates those responsibilities. Its native EditBuffer owns text,
cursor movement, word boundaries, selection, and undo history. Its editable
renderable owns viewport and selection presentation. Textarea maps key chords
to named editor actions, and Input specializes that stack with one-line
normalization, length limits, and commit behavior.

Cooper should adopt that conceptual split without importing OpenTUI's native
rope, TypeScript API, or backend implementation. Framework behavior remains
Ard-owned. A single-line value is small enough for immutable Ard `Str` values;
a rope or native editor backend is premature until a multiline control and
benchmarks demonstrate the need.

Terminal input is not a blocker. Vaxis already reports normalized key names,
press/repeat/release state, and Shift, Ctrl, Alt, and Super modifiers. Cooper's
backend bridge preserves those fields in `KeyEvent`, so bindings such as
Ctrl+W can be resolved in Ard.

## Decision

### Ard-native editor model

Add a root-level `editor.ard` module containing a UI-independent mutable editor
state. It owns:

- the immutable text value;
- a UTF-8 byte cursor normalized to grapheme boundaries;
- an optional UTF-8 byte selection anchor;
- grapheme-safe insertion, replacement, movement, and deletion;
- editor word-boundary navigation;
- action dispatch;
- undo and redo history when history is implemented.

The editor does not own Node references, Context, styles, placeholder content,
terminal-cell measurement, layout, focus, global selection generations,
validation callbacks, or application event delivery.

The initial action vocabulary is:

```ard
enum Action {
  move_left,
  move_right,
  move_start,
  move_end,
  move_word_backward,
  move_word_forward,
  select_left,
  select_right,
  select_start,
  select_end,
  select_word_backward,
  select_word_forward,
  select_all,
  delete_backward,
  delete_forward,
  delete_word_backward,
  delete_word_forward,
  delete_to_start,
  delete_to_end,
  undo,
  redo,
  submit,
}
```

Actions return value data describing whether they were handled and whether
text, cursor, or selection changed. `submit` is a request; `Input` continues to
own minimum-length validation and change/submit callbacks.

### Input adapter responsibilities

`Input` retains:

- one-line newline removal and `min_length`/`max_length` policy;
- focus commit baselines and input/change/submit callbacks;
- the horizontal terminal-cell viewport and cursor painting;
- mouse cell-to-grapheme mapping;
- global selection generation, clipping, translated geometry, and fragments;
- conversion from internal byte positions to public display-cell ranges;
- pointer-only edge panning and selection reconciliation;
- styles, placeholder behavior, Node lifecycle, and application listeners.

The editor's optional anchor represents logical editable selection, including a
collapsed anchor. Cooper's global selection metadata remains separate. This is
required so geometry reconciliation does not couple the editor model to the
retained runtime.

`set_value` resets editor history, moves the cursor to the end, and clears local
and global selection. Maximum-length capacity is calculated after hypothetical
selection removal so replacement remains atomic.

### Word semantics

Word operations are grapheme-safe and use editor-oriented Unicode classes:

1. whitespace is skipped before a backward word operation and after a forward
   word operation;
2. letters, numbers, marks, and connector punctuation form word runs;
3. punctuation and symbols form separate runs;
4. no operation splits a grapheme, emoji sequence, combining sequence, or
   regional-indicator pair;
5. CJK, emoji, apostrophes, underscores, punctuation, and tabs receive explicit
   deterministic tests.

Cooper may use the existing `go-uucode` Unicode properties at the Ard boundary,
but the movement policy and state transitions remain implemented in Ard. Full
UAX #29 conformance is not required for the first implementation; observable
editor behavior is the contract.

### Default CLI profile

Input resolves exact key names and modifiers. Omitted modifiers mean false; a
binding never treats an unspecified modifier as a wildcard. Release events are
ignored. Press and repeat execute the same action. Bound no-op actions remain
handled, while unmatched non-text keys are ignored. Printable fallback is
accepted only without Ctrl, Alt, or Super so control sequences cannot become
text accidentally.

The default single-line profile is:

| Keys | Action |
| --- | --- |
| Left, Ctrl+B | move left |
| Right, Ctrl+F | move right |
| Shift+Left, Shift+Ctrl+B | select left |
| Shift+Right, Shift+Ctrl+F | select right |
| Home, Ctrl+A, Super+Left | move start |
| End, Ctrl+E, Super+Right | move end |
| Shift+Home, Shift+Ctrl+A, Shift+Super+Left | select start |
| Shift+End, Shift+Ctrl+E, Shift+Super+Right | select end |
| Alt+B, Alt+Left, Ctrl+Left | move word backward |
| Alt+F, Alt+Right, Ctrl+Right | move word forward |
| corresponding Shift chords | select by word |
| Backspace | delete backward |
| Delete, Ctrl+D | delete forward |
| Ctrl+W, Ctrl+Backspace, Alt+Backspace | delete word backward |
| Alt+D, Alt+Delete, Ctrl+Delete | delete word forward |
| Ctrl+U | delete to start |
| Ctrl+K | delete to end |
| Super+A | select all |
| Super+Z, Ctrl+- | undo |
| Shift+Super+Z, Ctrl+. | redo |
| Return | submit |

Ctrl+A remains line start rather than select-all to preserve native CLI/readline
expectations. For single-line Input, line start/end and buffer start/end are the
same operation. A future Textarea may add distinct line, visual-line, buffer,
and vertical actions without changing existing variants.

### Binding representation and customization

Bindings are enum-backed value data rather than retained functions:

```ard
struct KeyBinding {
  name: Str,
  action: Action,
  shift: Bool?,
  ctrl: Bool?,
  alt: Bool?,
  super: Bool?,
}
```

Resolution is deterministic and ordered. The first implementation keeps the
default profile internal while action semantics stabilize. Existing ordered
`on_key` listeners and `prevent_default` remain the application override
mechanism.

A later public API may expose `default_key_bindings`, `perform`, and complete
binding replacement. Public merging, unbinding, aliases, and conflict behavior
are deferred until one implementation and a second editable control establish
the reusable shape.

### History transactions

History is added after pure action extraction and default keybindings are
stable. It follows these rules:

- one paste, selected replacement, word deletion, or kill action is one undo
  transaction;
- rejected edits create no history;
- a new edit clears redo history;
- `set_value` clears history;
- undo restores value, cursor, and logical anchor together;
- movement and selection terminate insertion coalescing;
- history storage is bounded before it becomes public API.

Until history lands, undo and redo actions are recognized and handled as no-ops
so their key chords never become text.

### Delivery order and callbacks

User key listeners continue to run before Input's built-in action resolver.
`prevent_default` suppresses built-in editor actions. The editor transaction and
selection synchronization complete before `on_input` runs. A text-changing
action emits exactly one input callback. Movement, selection, rejected edits,
and bound no-ops emit none.

## Implementation plan

1. Characterize unmatched, modified, repeat, release, callback, selection, and
   maximum-length behavior.
2. Add pure editor state and tests, then migrate Input's logical value, cursor,
   and anchor without observable changes.
3. Add action dispatch, word operations, and the default CLI profile.
4. Add PTY coverage for Ctrl, Alt, Super, repeat, and keypad normalization.
5. Add bounded transaction history and undo/redo.
6. Reassess a public keybinding API when Textarea or another editor consumes the
   same model.

Each phase keeps Ard formatting and checks, all Ard and Go tests, all example
PTY tests, and benchmark smoke passing.

## Consequences

- Input gains familiar terminal editing without adding backend interop.
- Logical editor behavior becomes deterministic and directly testable without a
  renderer.
- Input becomes an adapter over a reusable model suitable for a future
  Textarea.
- Selection integration remains complex because logical byte positions, public
  display-cell ranges, and global screen geometry intentionally use different
  units.
- Unicode word behavior requires explicit fixtures and will not automatically
  equal every shell or platform editor.
- History and configurable keymaps add state and API surface, so they are phased
  behind the stable action model.
- A rope, extmarks, syntax state, kill ring, clipboard commands, and multiline
  visual movement remain out of scope.

## Related

- [ADR 0002: Define Application API](./0002-define-application-api.md)
- [ADR 0003: Define Interaction, Focus, and Selection](./0003-define-interaction-focus-and-selection.md)
- [OpenTUI Input](https://opentui.com/docs/components/input)
- [OpenTUI keyboard input](https://opentui.com/docs/core-concepts/keyboard)
