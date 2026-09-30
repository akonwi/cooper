# Commands and keymaps

`cooper/keymap` provides Runtime-owned keyboard scopes and typed commands.
It requires Ard v0.43.0. See the runnable [Hacker News reader](../examples/cui_hackernews.ard)
and [design decision](adrs/0024-define-keymaps-and-commands.md).

The reader uses page-local focus scopes for selection, scrolling, expansion,
pagination and retries, with an outer scope for feed switching and Back.
Movement and feed selection take typed arguments; activation obtains the current
selected item with `with_lazy`. Its footer reads eligible shortcuts from CUI
discovery, so Back disappears in the feed and Open disappears on an empty page.
Ctrl+C remains the Runtime's automatic exit policy.

## Commands are independent of keys

```ard
use cooper/keymap

let save = keymap::command(
  "document.save",
  "Save document",
  fn(path: Str) Bool {
    document.save(path)
  },
  enabled: fn() Bool { document.dirty },
  group: "document",
)
let quit = keymap::simple_command("app.quit", "Quit", fn() Bool {
  runtime.destroy_live()
  true
})

let _ = save.invoke("notes.txt")
let _ = quit.invoke()
```

`command` infers `TypedCommand<Args>` from the handler. Use a struct for multiple
arguments. `simple_command` returns `SimpleCommand`, with no dummy argument.
Both implement the non-generic `Command` metadata trait, so `[save, quit]` can
be a heterogeneous catalog. IDs and titles must be nonempty; catalog IDs must
be unique within a layer at registration.

`save.with("notes.txt")`, `save.with_lazy(fn() Str { document.path })`, and
`quit.with()` all return non-generic `Invocation` values. Argument types are
checked at compile time. Lazy providers should capture a mutable model when
they need current state; read-only scalar captures are snapshots in Ard.

`enabled: fn() Bool` defaults to true and is checked on direct invocation as
well as keyboard dispatch, before any lazy argument provider runs. Discovery
calls availability predicates, never providers or handlers. Keep predicates
side-effect-free. Returning false declines an invocation and permits fallback;
return true when handled, including a handled operation that changed nothing.

## Register a scope

```ard
let keys = keymap::layer(
  [
    keymap::binding(keymap::key("s", ctrl: true), save.with_lazy(fn() Str {
      document.path
    })),
    keymap::binding(keymap::key("q", ctrl: true), quit.with()),
  ],
  commands: [save, quit],
  scope: keymap::focus_within(editor),
  priority: 10,
)
let remove = keymap::register(runtime, keys)
defer remove()
```

The default scope is `application()`. `focus(control)` requires exact focus;
`focus_within(control)` includes descendants. Hidden or detached focus scopes
are inactive. Scopes do not make controls focusable or implement Tab traversal.
A scoped registration is cleaned up when its original target is destroyed;
remove and register again to transfer its ownership to another target.
Runtime destruction removes all registrations. Disposers are idempotent.

Eligible layers run by descending priority, then specificity (exact focus,
nearest focused ancestor, application), then newest registration. Bindings
within a layer run in declaration order. Update a registered layer in place
to preserve its precedence. Registration and mutation belong on the UI thread.
Dispatch snapshots bindings; a removed registration or invalidated focus route
does not continue handling the same key.

`Key` uses the same canonical names as `KeyEvent`: for example `return`,
`page_up`, and `left`. Modifiers match exactly; omitted flags mean false.
`Key.label()` formats labels such as `Ctrl+S`. Application bindings default to
`Trigger::press`; opt into `press_or_repeat` or `release` explicitly.

Existing event ordering is preserved: Runtime raw listeners, automatic Ctrl+C
exit, focused listeners/CUI bubbling, keymaps, then built-in control defaults.
`prevent_default()` suppresses mappings and defaults. A focused listener's
`stop_propagation()` skips keymaps but retains that control's default behavior.
Disable the application's existing Ctrl+C exit option to bind Ctrl+C yourself.

## Remap controls without replacing their behavior

Input, TextArea, Select, TabSelect, ScrollBox, and Scrollbar expose typed
`Action` values, `perform(action)`, `key_bindings()`, `set_key_bindings(map)`,
and `default_bindings()` helpers. Public action types and default-map helpers
are also available through `cooper/ui`.

```ard
let defaults = ui::default_input_bindings()
let custom = keymap::rebind(
  defaults,
  ui::InputAction::submit,
  [keymap::key("s", ctrl: true)],
)
field.set_key_bindings(custom)
let _ = field.perform(ui::InputAction::submit)
keymap::changed(runtime)
```

Control maps are immutable values: use the returned map from `bind`, `unbind`,
or `consume`. `bind` replaces an exact key/trigger pair; `keymap::rebind`
replaces all aliases for an action. `unbind` permits normal fallback, whereas
`consume` handles the key without running an action. Empty maps disable mapped
actions, not ordinary text insertion. Control mappings default to
`press_or_repeat`. `perform` retains validation, callbacks and selection
semantics; its result means handled, not changed. ScrollBox retains its
movement-only handling so nested scrolling can fall back.

Application layers similarly support `bind(binding)`, `unbind(key)`, and
`rebind(invocation, keys)`, mutating the layer in place.

## CUI and shortcut discovery

CUI containers and interactive controls accept `commands`, `bindings`, `binding_scope`, and
`binding_priority`. Their default scope is `focus_within` the mounted view.
Input, TextArea, Select, TabSelect, and ScrollBox additionally accept typed
`key_bindings` replacement maps. Reconciliation updates the retained control
and layer without changing registration order, and unmount removes the layer.
Raw `on_key` handlers still bubble before mappings run.

Lifecycle contexts provide `ctx.bind_keys(layer)`, `ctx.on_keys_change(handler)`,
`ctx.shortcuts()`, and `ctx.commands()`. These subscriptions are mount-owned;
command execution and discovery notifications invalidate the component.

`keymap::shortcuts(runtime)` returns registered shortcuts plus the focused
control's effective map, including command metadata, key/trigger, scope,
priority, eligibility and shadowing. `keymap::commands(runtime)` includes
unbound catalog entries. Build menus and help text from these values rather
than duplicating key-label strings.

`shadowed` means an earlier eligible mapping covers that key's entire trigger;
it is advisory, since a handler may decline and raw listeners may prevent
dispatch. A press-only mapping does not wholly shadow press-and-repeat.
Control defaults always follow application layers, irrespective of their
reported priority. Automatic Ctrl+C exit makes corresponding press bindings
ineligible.

Use `keymap::on_change(runtime, handler)` to subscribe. Focus and registration
changes notify automatically. After imperative map changes, layer edits, or
changes to state used by `enabled`, call `keymap::changed(runtime)` to refresh
subscribers. Queries themselves always read current state. CUI tracks its
declarative maps and command availability during reconciliation.
