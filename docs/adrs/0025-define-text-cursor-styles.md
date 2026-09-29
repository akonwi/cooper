# 0025: Define Text Cursor Styles

## Status

Proposed

## Context

Input and TextArea show the terminal's hardware cursor at the caret while they
are focused. Cooper currently hardcodes a steady beam: `Runtime.present` passes
`vaxis::CursorBeam` to `Window.ShowCursor`, and neither `paint::Cursor` nor the
controls carry style information. Users who have configured a block or
underline cursor in their terminal see a beam anyway, and applications cannot
change the shape, for example to show a block in a vim-style normal mode.

Terminals select the cursor style with DECSCUSR (`CSI Ps SP q`). Values 1–6
select a blinking or steady block, underline, or bar. `Ps = 0` asks the
terminal to use its own default, which terminals such as Ghostty, kitty,
WezTerm, and iTerm2 take from the user's configuration.

Vaxis represents these values as `CursorStyle`, including `CursorDefault` (0).
`showCursor` writes the requested style every time it positions a visible
cursor, and the writer also emits it when only the style changed. At startup
Vaxis sends a DECRQSS query for the current cursor style and stores the reply
in the private `userCursorStyle` field. `Suspend` and `Close` restore that value
and show the cursor, so shell-owned cursor state survives Cooper sessions
without Cooper doing anything.

Only one hardware cursor exists, and it belongs to the focused editable
control. The cursor style is a paint-time property of that control, not
application chrome like the terminal title (ADR 0012).

## Decision

### Public value

Add `ui/cursor.ard` with an Ard-native enum. Each variant corresponds to exactly
one DECSCUSR value:

```ard
enum CursorStyle {
  terminal,
  block,
  blinking_block,
  underline,
  blinking_underline,
  beam,
  blinking_beam,
}
```

`terminal` means "use the terminal's configured style" and maps to
`vaxis::CursorDefault`. Explicit variants map to the corresponding Vaxis
constant. `ui.ard` exposes the type as `ui::CursorStyle`.

A single enum is used instead of a shape plus a blink flag. A flag would allow
the meaningless combination "terminal default plus blink", so it would need a
panic or a silent rule to reject it. The enum also matches DECSCUSR exactly.
`beam` follows Vaxis and common editor terminology; xterm calls the same
style "bar".

### Control API

Input and TextArea accept an optional constructor argument and expose accessors:

```ard
ui::input(ctx, cursor_style: ui::CursorStyle::block)

impl Input {
  fn cursor_style() ui::CursorStyle
  fn mut set_cursor_style(value: ui::CursorStyle)
}
```

TextArea has the same shape. The default is `CursorStyle::terminal` for both
controls. Setting the same value again does nothing. Setting a different value
requests a repaint and does not affect layout, editor state, selection, or
focus.

No application-wide or Runtime-level default is added. An application that
wants one style everywhere can wrap the constructors. An application that
switches modes calls `set_cursor_style` on the affected control. A global
default can be added later without changing the per-control contract.

### Declarative components

The experimental declarative `cui::input` and `cui::text_area` views accept the
same optional `cursor_style` argument, defaulting to `CursorStyle::terminal`.
The renderer applies it through `set_cursor_style` on every update, so
declarative applications do not need a control ref to choose a style.

### Paint and presentation

`paint::Cursor` gains a `style: CursorStyle` field, and
`paint::Context.show_cursor` takes an optional style argument that defaults
to `CursorStyle::terminal`. The paint API remains internal under `core/`. If several nodes request a cursor in one
frame, the last request wins, as it does today, so focused-control ownership
decides both position and style.

`Runtime.present` converts `CursorStyle` to `vaxis::CursorStyle` at the
backend boundary. No other module imports Vaxis cursor constants.

Cooper does not query, cache, or expose the terminal's detected style. The
`terminal` variant covers adaptation without a round trip, and it also follows
configuration changes made while the application is running. Exposing
Vaxis's detected `userCursorStyle` would require a new accessor in the Vaxis
fork and an optional result, because terminals may not answer DECRQSS. It is
deferred until a use case needs the concrete shape, such as painting a
simulated cursor.

### Lifecycle

Restoration stays with Vaxis. On suspend and destruction, Vaxis writes the
style reported at startup (or `CursorDefault` when the terminal did not
answer) and shows the cursor. On resume, the next frame writes the focused
control's style again. Cooper adds no additional restore logic.

### Testing

`Frame.cursor_style()` returns `CursorStyle?` next to the existing
`cursor_x()` and `cursor_y()` accessors on the headless test frame returned by
`TestApp.frame()`. It is `none` when no cursor is shown.

Headless tests cover:

- the `terminal` default for Input and TextArea;
- constructor and setter values, idempotent setters, and repaint on change;
- no cursor style when unfocused or when the caret is outside the viewport;
- the focused control's style winning when focus moves between controls with
  different styles.

PTY tests verify the emitted `CSI 0 SP q` for the default and `CSI 2 SP q` /
`CSI 6 SP q` for explicit styles. They also verify that a style-only change
emits a sequence without cursor movement, and that the startup style is
restored on suspend and quit.

## Consequences

The default visible behavior changes. Focused inputs now follow the user's
terminal configuration instead of always showing a steady beam. For users with
a configured block cursor, Cooper inputs look like the rest of their terminal.
Applications that relied on the beam must opt in with `CursorStyle::beam`.

Adaptation is exactly as good as the terminal's DECSCUSR support. Terminals
that ignore DECSCUSR keep their current cursor. A few older terminals treat
`Ps = 0` as a blinking block rather than as the user's configured style.
Multiplexers such as tmux forward DECSCUSR according to their own
configuration. Cooper cannot detect these cases and does not try to.

Cooper still cannot report which style the terminal actually uses.

## Related

- [ADR 0004: Define Input Editor State and CLI Keybindings](./0004-define-input-editor-and-keybindings.md)
- [ADR 0011: Define the Multiline TextArea](./0011-define-multiline-text-area.md)
- [ADR 0012: Define Terminal Title Updates](./0012-define-terminal-title-updates.md)
- [ADR 0015: Define Package Entry Points and the UI Namespace](./0015-define-package-entry-points-and-ui-namespace.md)
- [Vaxis `CursorStyle`](https://pkg.go.dev/git.sr.ht/~rockorager/vaxis#CursorStyle)
- [xterm DECSCUSR](https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h4-Functions-using-CSI-_-ordered-by-the-final-character-lparen-s-rparen:CSI-Ps-SP-q.1D81)
