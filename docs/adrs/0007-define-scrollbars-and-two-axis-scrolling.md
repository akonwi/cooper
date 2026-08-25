# 0007: Define Scrollbars and Two-Axis Scrolling

## Status

Accepted

## Context

Cooper's ScrollBox is a focusable vertical scrolling container. It owns
requested and effective vertical offsets, clamps them after layout, translates
child geometry, clips paint and hit testing, reveals focused descendants, and
supports wheel and keyboard movement with nested fallback. It has no visible
scroll position indicator and no direct pointer mechanism for moving through a
large viewport.

OpenTUI composes every ScrollBox from a viewport and public vertical and
horizontal ScrollBars. Its standalone ScrollBar wraps a proportional slider,
auto visibility, optional arrows, pointer dragging, direct track presses,
keyboard control, styling, and change notification. Hidden automatic bars retain
their layout extent, avoiding content reflow as overflow appears and disappears.

Cooper should adopt the useful behavior, not OpenTUI's TypeScript object model.
Scroll state, geometry, controls, interaction, and lifecycle remain Ard-owned.
The internal layout backend continues to calculate dimensions, while Cooper
owns offset semantics and cells.

Cooper currently implements only vertical scrolling. Horizontal ScrollBox
support is not deferred indefinitely, but it must follow validation of the
standalone primitive and vertical integration so two-axis behavior builds on a
stable bar, pointer, and layout model.

## Decision

### One standalone Scrollbar primitive

Add a public `scrollbar.ard` module with one configurable Scrollbar supporting
both orientations:

```ard
enum Orientation {
  vertical,
  horizontal,
}

enum Visibility {
  automatic,
  always,
  hidden,
}

struct State {
  position: Int,
  viewport_size: Int,
  content_size: Int,
}

struct Options {
  visibility: Visibility,
  show_arrows: Bool,
  scroll_step: Int,
  theme: Theme,
}
```

Provide helper constructors for validated State, Theme, and Options values.
Sizes and positions use Ard Int, sizes must be non-negative, scroll step must be
positive, and position is clamped to `0...max(0, content_size -
viewport_size)`. Theme glyphs must each occupy exactly one terminal cell.

Scrollbar exposes state snapshots, non-notifying state synchronization,
position and maximum getters, option/theme setters, the common control API, and
idempotently removable change listeners. User interaction updates its local
position and notifies listeners with the resulting position. External state
changes call `set_state`; this reflection path does not emit change and therefore
does not create feedback loops.

Standalone Scrollbars are focusable. The built-in bars owned by ScrollBox use
the same primitive but are not separate focus-traversal stops.

### Track, thumb, arrows, and interaction

Scrollbar occupies one cell across its minor axis. Its usable track is the
major-axis extent minus two cells when arrows are enabled and enough space is
available. The thumb length is proportional to `viewport_size / content_size`,
clamped to at least one track cell. The thumb start maps the effective position
onto the remaining track range. Tiny and zero-sized bars remain bounded and do
not divide by zero.

Default vertical glyphs are a light track, heavy thumb, up arrow, and down
arrow. Horizontal defaults use the corresponding horizontal track, thumb, left
arrow, and right arrow. Track, thumb, and arrows have independently configurable
text styles and one-cell glyphs.

Pointer behavior follows OpenTUI's direct slider model:

- a left press on the thumb records the pointer-to-thumb offset;
- a left press elsewhere on the track jumps the thumb toward that position and
  begins a drag;
- captured drag events clamp beyond either end and continuously update position;
- release or drag-end clears drag state;
- an arrow press moves one configured step.

Arrow press-and-hold repetition is initially omitted. It requires a general
control-lifetime timer convention and does not change the primitive's state or
event model.

Focused standalone Scrollbars handle orientation-appropriate arrows, Page
Up/Down, Home, and End. Page movement uses one viewport. Built-in ScrollBox key
behavior remains owned by ScrollBox so its existing focus and nested-event
semantics do not change.

### Visibility and stable gutters

`automatic` is the default. It paints and accepts interaction only when content
exceeds the viewport, but it keeps a stable one-cell layout gutter. `always`
paints even when no movement is possible; its full-track thumb communicates that
state. `hidden` removes the primitive from layout and interaction entirely.

ScrollBox enables its built-in vertical Scrollbar by default with automatic
visibility, a stable one-cell gutter, and arrows disabled. Applications may
choose always-visible or hidden and may configure glyphs, styles, step, and
arrows.

### ScrollBox composition

Refactor ScrollBox from one scrolling Node into an Ard-owned private
composition while preserving its public facade:

```text
ScrollBox root
└── row wrapper
    ├── viewport column
    │   ├── scrolling viewport
    │   └── future horizontal Scrollbar
    └── vertical Scrollbar
```

Application children belong to the scrolling viewport. Public `add`, indexed
reorder, `remove`, `child_count`, scroll metrics and movement, reveal, style,
focus, listener, layout, and destruction methods deliberately delegate to the
correct public root or private viewport. Internal parts are not exposed for
reparenting or destruction.

The viewport Node remains the authoritative ScrollBox state. Before painting,
the root synchronizes its vertical bar from the viewport's effective offset,
viewport height, and content height without notification. Bar change callbacks
call the viewport's validated scroll setter. Scroll movement from wheel, keys,
focus reveal, resize, content mutation, and direct API calls therefore converges
on one offset.

Non-recursive ScrollBox destruction detaches and preserves application children
before recursively destroying private composition nodes. Recursive destruction
continues to destroy the complete application subtree. Copies of ScrollBox and
Scrollbar facades share retained identity and listener state.

### Validation checkpoint

Before horizontal ScrollBox behavior is added, deterministic headless and PTY
coverage must validate:

- proportional geometry at start, middle, end, no-overflow, and tiny extents;
- automatic, always, and hidden layout and paint behavior;
- track presses, thumb dragging beyond both ends, arrows, and keyboard input;
- non-notifying reflection and exactly-once change callbacks;
- ScrollBox wheel, keys, focus reveal, nested fallback, clipping, translated hit
  testing, resize, and content growth/shrink;
- stable gutters and existing example behavior;
- detach, reparent, recursive/non-recursive destruction, and listener cleanup.

### Horizontal ScrollBox phase

After that checkpoint passes, add horizontal scrolling in the next implementation
phase using the already validated horizontal Scrollbar. Add Ard-owned horizontal
requested/effective offsets and child geometry translation rather than backend
or application-local state.

The public API gains horizontal position, requested offset, maximum, and content
width metrics; horizontal movement; coordinate movement; and two-axis child
reveal. Shift+vertical wheel maps to horizontal movement. Nested wheel fallback
stops only an axis that actually moved. Keyboard behavior remains predictable
and orientation-aware.

The horizontal bar occupies the bottom of the viewport column. When both bars
are enabled, the bottom-right corner belongs to the vertical bar, matching the
composition above. Selection fragments, hit testing, focus reveal, clipping,
and translated geometry must operate correctly with both offsets.

Horizontal support is complete only after equivalent headless and PTY validation
passes. Scroll acceleration, sticky edges, virtualization, and selection-edge
auto-scroll remain separate decisions.

## Consequences

ScrollBox gains an always discoverable scrolling affordance without layout
jumps as vertical overflow changes. Applications can also compose the same
Scrollbar with app-local scroll models before Cooper grows additional built-in
containers.

Default automatic vertical gutters reduce ScrollBox content width by one cell.
Existing examples and snapshots may require intentional width-sensitive updates.
Applications that require the previous full width can configure hidden
visibility.

The private ScrollBox tree becomes more complex, so identity, focus routing,
destruction, and public child operations require stronger tests. In return,
paint and hit testing use normal retained composition instead of ScrollBox-only
overlay exceptions.

Separating primitive validation from horizontal integration limits simultaneous
sources of failure while committing Cooper to two-axis scrolling as the next
phase rather than leaving it indefinitely deferred.

## Related

- [ADR 0002: Define Application API](./0002-define-application-api.md)
- [ADR 0003: Define Interaction, Focus, and Selection](./0003-define-interaction-focus-and-selection.md)
- [OpenTUI ScrollBar](https://github.com/sst/opentui/blob/main/packages/core/src/renderables/ScrollBar.ts)
- [OpenTUI ScrollBox](https://github.com/sst/opentui/blob/main/packages/core/src/renderables/ScrollBox.ts)
