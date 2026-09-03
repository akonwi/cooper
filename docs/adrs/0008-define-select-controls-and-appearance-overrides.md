# 0008: Define Select, TabSelect, and Appearance Overrides

## Status

Accepted. Package paths and module placement are superseded by
[ADR 0015](./0015-define-package-entry-points-and-ui-namespace.md).

## Context

OpenTUI names its always-expanded option list `Select`, but web and native UI
conventions use Select for a compact, non-editable field that opens an anchored
option menu. Cooper should follow the broader convention rather than expose an
always-expanded list as a built-in primitive. Applications can compose
persistent lists from Box, Text, scrolling, and their own domain behavior.

OpenTUI also provides TabSelect. Tabs remain a useful built-in control with a
similar option model, highlight/selection state, and callbacks, but a distinct
presentation.

Scrollbar introduced a public per-control `Theme` value. That name and its
eagerly resolved concrete styles could be confused with a future holistic
application theme and make dynamic theme changes harder to propagate.

Ard reserves the lowercase word `select`, so a `select.ard` module must be
imported with an alias and `ui::select` cannot be a constructor name.

## Decision

### Select is a compact native-style field

Add a public `Select` retained control in `select.ard`. It occupies one row and
shows either its committed option or a configurable placeholder. A trailing
`▾` indicates the closed state.

Click, Enter, Space, Up, or Down focuses and opens an anchored option menu. The
menu is an absolutely positioned private Root overlay, so it does not increase
the Select's layout height, push surrounding content, or lose to later siblings.
While open:

- Up/Down and j/k move the transient highlight;
- shifted movement advances by the configured fast step;
- wheel input and the optional vertical Scrollbar pan the menu viewport independently, including past the highlighted option;
- clicking an option or pressing Enter commits and closes;
- Escape and blur close without committing;
- keyboard movement reveals the highlight within a retained bounded viewport;
- descriptions, wrapping, pointer input, and indicator visibility remain
  configurable.

The private portal is excluded from Root's public child model and reattaches to
Select before close or destruction. Focus, attachment generation, and structural
revision are revalidated after callbacks
so a stale pointer route cannot activate replaced or reparented data.

`select_control::new` constructs Select. Since `ui::select` is reserved,
`ui.ard` exposes `ui::select_input`.

### Keep TabSelect

Keep horizontal `TabSelect` with fixed-width tabs, optional underline and
highlighted description, overflow arrows, wrapping, keyboard navigation, and
mouse activation. `select_control::tabs` and `ui::tab_select` construct it.
Select and TabSelect share the Ard-owned option/state engine internally, while
remaining distinct public control names.

An always-expanded ListBox and an editable Combobox are not built-in controls.

### Options and two distinct states

An option is open value data:

```ard
struct Option {
  label: Str,
  description: Str?,
  value: Str?,
}
```

Controls snapshot the option array. String values keep the public domain
Ard-native and avoid exposing `Any`; applications with richer models map the
stable index or string value to their own data.

Controls retain two optional states:

- `highlighted`: the transient navigation cursor and preview;
- `selected`: the last committed option shown by a closed Select.

A non-empty control highlights the first option by default but starts without a
committed selection. Empty controls expose neither state and are inert.
Replacing options preserves and clamps existing indexes without emitting a
user-action callback.

Listener semantics are:

- `on_highlight` fires for an actual cursor transition;
- `on_change` fires when committed selection changes;
- `on_submit` fires for every valid Enter or click activation, including a
  repeated submission of the committed option.

Listener removal is idempotent and emissions use stable snapshots.

### Appearance is a local patch, not a Theme

Reserve `theme::Theme` for a future Context-owned holistic system of semantic
roles. Rename `scrollbar::Theme` and `Options.theme` to
`scrollbar::Appearance` and `Options.appearance`.

Select, TabSelect, and Scrollbar Appearance structs contain optional glyph and
SpanStyle patches. Public options retain unresolved patches. Resolution order
is:

```text
framework defaults
→ future Context Theme semantic roles
→ local control Appearance
→ focused/highlighted/selected interaction state
```

Select validates marker width, one-cell trigger/underline/arrow glyphs,
positive visible-menu size, positive tab width and fast step, and bounded
non-negative item spacing.

### Lifecycle

Select and TabSelect are focusable. Private popup and Scrollbar nodes are not
separate focus-traversal stops and are always destroyed with their owner.
Facade copies share identity and listeners. Destruction and structural mutation
are safe during focus and selection callbacks.

## Consequences

Cooper's Select matches conventional native and web expectations: compact while
closed, value-bearing, and menu-driven when open. TabSelect remains available
without introducing an always-expanded ListBox or editable Combobox primitive.

Select introduces an internal Root-overlay marker so portal nodes do not affect
public child counts or indexed application children. A future general overlay
service can reuse that mechanism.

Renaming Scrollbar Theme is a breaking source change. Doing it before release
prevents per-control visual bundles from hardening into a competing global theme
concept.

## Related

- [ADR 0002: Define Application API](./0002-define-application-api.md)
- [ADR 0003: Define Interaction, Focus, and Selection](./0003-define-interaction-focus-and-selection.md)
- [ADR 0007: Define Scrollbars and Two-Axis Scrolling](./0007-define-scrollbars-and-two-axis-scrolling.md)
