# Application API proposal

Status: proposed for review. This is not yet a compatibility guarantee.

## Scope

This proposal covers Cooper's imperative application API. It deliberately does
not define a supported custom `Renderable` API yet. Cooper's own primitives and
runtime will exercise that protocol until the core is stable enough to extract
a smaller public authoring contract.

The model follows OpenTUI's imperative
[`@opentui/core`](https://opentui.com/docs/core-concepts/renderer) API rather
than its React or Solid bindings.

## Proposed application shape

```ard
use cooper/app
use cooper/box
use cooper/text

fn main() {
  let application = app::new().expect("create Cooper app")
  let root = box::new(application.context)
  root.add(text::new(application.context, content: "Hello"))
  application.run(root).expect("run Cooper app")
}
```

`App` is a one-shot handle value:

```ard
struct App {
  context: mut context::Context,
}

fn new() App!Error

impl App {
  fn run(root: mut node::Renderable) Void!Error
  fn close()
}
```

- `context` is a field, not a getter. Applications pass it to Cooper
  constructors.
- `run` owns the terminal event loop and blocks until shutdown.
- `run` always restores the terminal and closes the App before returning,
  including on error.
- `close` is idempotent and supports abandoning an App before `run`.
- Calling `run` after closure is a programmer error.
- Cooper constructors create persistent mutable controls. Updating a control
  requests another frame without rebuilding the tree.

The initial application-facing controls remain `Box`, `Text`, `Input`, and
`ScrollView`. Their exact mutation and callback APIs will be reviewed
separately.

## Relationship to OpenTUI

OpenTUI's core API is an imperative retained tree:

```ts
const renderer = await createCliRenderer()
const panel = new BoxRenderable(renderer, {})
panel.add(new TextRenderable(renderer, { content: "Hello" }))
renderer.root.add(panel)
```

Cooper adopts the same underlying shape:

| OpenTUI core | Cooper |
| --- | --- |
| `createCliRenderer()` | `app::new()` |
| `CliRenderer` owns the terminal, scheduling, input, and root | `App` owns the terminal, event loop, scheduling, and Context |
| Renderer implements `RenderContext` | `App.context` is the constructor capability |
| `new BoxRenderable(renderer, options)` | `box::new(application.context, ...)` |
| `new TextRenderable(renderer, options)` | `text::new(application.context, ...)` |
| `parent.add(child)` | `parent.add(child)` |
| Mutable renderable properties schedule rendering | Primitive setters mutate retained state and request rendering |
| Each renderable owns Yoga layout state | Each Cooper renderable owns a persistent Node with internal Yoga state |
| `renderSelf()` draws after layout | The internal `draw()` callback draws after layout |
| Renderer destruction restores the terminal | App shutdown restores the terminal and destroys its Context-owned tree |

The important inspiration is not TypeScript syntax. It is the ownership model:

1. create one terminal runtime;
2. pass its render context to retained control constructors;
3. build one persistent mutable tree;
4. mutate existing controls directly;
5. let the runtime own layout, drawing, input routing, and terminal output.

Cooper keeps this model Ard-native. Concrete Ard structs own control state while
a persistent Node owns hierarchy, layout, geometry, focus, and attachment
state. Tess/Yoga and Vaxis remain implementation details.

## Intentional differences from OpenTUI

### App and context are separate

OpenTUI passes its renderer directly to renderable constructors because
`CliRenderer` implements `RenderContext`. Cooper exposes the narrower
`App.context` capability instead of passing terminal ownership and runtime
services into every constructor.

### The root is passed to `run`

OpenTUI exposes `renderer.root` and applications attach their tree to it. Cooper
currently accepts one detached root in `application.run(root)`. This makes the
single running tree and its ownership explicit.

### Lifecycle is one-shot

OpenTUI starts demand-driven rendering after renderer creation and requires the
owner to call `renderer.destroy()`. Cooper's `run` is a blocking one-shot
operation that performs teardown before returning. `close` only covers an App
that will not be run.

### Custom renderables are deferred

OpenTUI supports subclassing `Renderable` and exposes Yoga measurement and
buffer drawing as an advanced API. Cooper is not committing to an equivalent
extension API yet. Its internal protocol currently has this general shape:

```ard
trait Renderable {
  fn node() mut Node
  fn mut mount(ctx: MountContext)
  fn draw(ctx: mut paint::Context)
  fn mut event(ctx: mut event::Context) event::EventResult
}
```

This remains implementation-facing. Core usage will determine which Node,
mount, draw, event, and measurement capabilities are eventually safe and useful
to publish.

## Deferred reviews

- primitive setters, callbacks, and focus controls;
- child insertion, removal, and reordering;
- Style construction and mutation;
- App configuration and global key policies;
- Cooper-owned event values;
- testing APIs;
- a first-class custom `Renderable` API.
