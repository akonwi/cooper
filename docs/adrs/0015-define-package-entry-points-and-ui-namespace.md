# 0015: Define Package Entry Points and the UI Namespace

## Status

Accepted

## Context

Cooper's implementation began as one Ard module per package-root file. That
made each domain easy to develop independently, but it made ordinary
applications import many sibling modules before constructing even a small
view:

```ard
use cooper/app
use cooper/box
use cooper/color
use cooper/event
use cooper/runtime
use cooper/style
use cooper/text
```

The existing `ui.ard` module already aliases built-in controls, but layout,
color, geometry, and interaction types still require separate imports. Adding
another package-root facade over the same flat implementation would improve the
short example without making the package organization express the intended
public model.

Tinear's complete Cooper implementation demonstrated both that applications can
compose custom views from Cooper's primitives and that the common application
surface naturally divides into two namespaces: application/runtime behavior and
UI construction.

Ard resolves a bare dependency import such as `use cooper` to `cooper.ard` and
allows `ui.ard` to coexist with modules beneath `ui/`. Ard does not provide
module-wide re-export syntax, so a curated UI entry point still aliases the
public declarations it exposes.

## Decision

### Two canonical entry points

Cooper's ordinary application API has two canonical imports:

```ard
use cooper
use cooper/ui
```

`cooper.ard` is the actual application entry point, not a compatibility facade.
It owns the `App` struct, its lifecycle and listener methods, and the fallible
`app(...)` constructor:

```ard
let application = cooper::app().expect("create Cooper app")
let title = ui::text(application.context, content: "Hello")
application.root.add(title)
application.run().expect("run Cooper app")
```

The package root also aliases the stable types commonly needed by application
and custom-view code, including `Runtime`, `Root`, and Cooper event values.
Runtime implementation and platform services remain in focused root modules;
the root entry point does not duplicate their implementation.

`ui.ard` is the curated entry point for view construction. It exposes:

- built-in control types and constructors;
- Style, Length, Edges, layout enums, and layout helpers;
- Color and color constructors;
- Point, Rect, Geometry, and geometry helpers;
- selection snapshots and ranges;
- rich-text values and helpers;
- Select, Scrollbar, and TextArea configuration values.

Names that would collide across domains remain qualified at the facade, such as
`ScrollbarState`, `SelectSelection`, and `TextStyle`.

### Physical UI namespace

UI implementation modules move beneath `ui/`:

```text
ui.ard
ui/
  box.ard
  color.ard
  editor.ard
  geometry.ard
  input.ard
  scroll_box.ard
  scrollbar.ard
  select.ard
  selection.ard
  style.ard
  text.ard
  text_area.ard
  text_area_layout.ard
```

Control and foundational modules remain focused and directly testable. The
shared editor and TextArea layout modules are implementation support and are not
re-exported through `ui.ard`.

Application-scoped capabilities stay at the package root:

```text
cooper.ard
animation.ard
clipboard.ard
event.ard
notification.ard
root.ard
runtime.ard
terminal_progress.ard
testing.ard
```

Unsupported retained/runtime machinery stays beneath `core/`, and backend
bindings stay beneath `ffi/core/backend/`.

### Dependency direction

Both entry points are dependency-graph leaves:

- implementation modules never import `cooper.ard`;
- UI implementation modules never import the `ui.ard` facade;
- runtime and core modules import foundational `cooper/ui/*` modules directly;
- controls may import Runtime, core mechanisms, and other focused UI modules;
- the UI facade alone gathers and aliases the supported UI vocabulary.

This prevents facade cycles such as `ui.ard -> ui/box.ard -> ui.ard` and keeps
implementation dependencies explicit.

### Focused modules and compatibility

Focused imports such as `cooper/runtime`, `cooper/testing`,
`cooper/animation`, and `cooper/ui/text` remain available when an application
needs a specialized namespace. The two entry points optimize the common path;
they do not require every advanced capability to occupy one namespace.

The previous package-root control paths and `cooper/app` are removed rather than
kept as forwarding shims. Cooper still has no compatibility commitment, and a
coordinated clean break avoids preserving a second misleading package layout.

## Consequences

- Small applications and custom views can normally use only `cooper` and
  `cooper/ui`.
- The package layout now communicates the distinction between application
  behavior and UI construction.
- `cooper.ard` is independently useful even for applications that construct no
  controls.
- `ui.ard` contains deliberate aliases because Ard lacks whole-module
  re-exports, but those aliases now front a coherent implementation namespace.
- Internal framework code must import focused leaf modules rather than either
  facade.
- Existing consumers must update imports and constructor qualification in one
  breaking migration.
- A literal `ui/internal/` directory is avoided because Ard's Go output is
  subject to Go's `internal` import rules; support boundaries remain documented
  instead of filesystem-enforced.

## Related

- [ADR 0002: Define the Application API](./0002-define-application-api.md)
- [ADR 0013: Consolidate Context into Runtime](./0013-consolidate-context-into-runtime.md)
- [Ard modules](https://ard.run/guide/modules/)
- [Ard dependencies](https://ard.run/guide/dependencies/)
