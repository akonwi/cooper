# 0023: Define Terminal Screen Modes

## Status

Accepted. Backend and Cooper implementation are pending.

This supersedes ADR 0002's requirement that Root always fill the
terminal: Root instead fills the App's rendering surface. Existing fullscreen
applications and component APIs remain compatible.

## Context

Cooper currently constructs Vaxis without a screen-mode option. Runtime sizes
layout and its paint buffer from `terminal.Window()`, copies cells into that
window, and passes cursor and mouse coordinates without a terminal-origin
translation. App owns one Runtime, Root, terminal session, and input stream.
Setting a child height changes layout, not terminal ownership or screen mode.

The references implement different contracts:

- OpenTUI exposes `alternate-screen`, `main-screen`, and `split-footer`.
  Main-screen still uses full-height geometry; it is not an inline renderer.
  Split-footer defaults to captured stdout and a bounded render surface. It
  seeds placement from the current cursor, moves down as output accumulates,
  and pins at the bottom. Its passthrough variant starts bottom-pinned instead.
- Cooper's pinned Vaxis fork exposes `PrimaryScreenOptions.RegionHeight` and
  `Append*`. It renders a live block relative to the current cursor, inserts
  appended output before it, and preserves the final block on close.

Inspected Vaxis at Cooper's pin
[`34e5202`](https://github.com/akonwi/vaxis/commit/34e5202041359d6d662fec66791dbcbfe07daa60)
and OpenTUI at
[`5eeed22`](https://github.com/anomalyco/opentui/commit/5eeed22a2f42a842d26c9bd000b06c02d245103c).
Vaxis's primary renderer is not yet sufficient for interactive Cooper controls:

- Writer flush places a visible cursor with absolute terminal coordinates. The
  next primary repaint assumes the cursor is still at the live block's end.
- Mouse events have terminal coordinates, without a primary-region origin.
- Region growth can move upward by the new height rather than the old occupied
  height before erasing, entering preceding output.
- Suspend/resume retains primary-render bookkeeping without re-establishing the
  region after external output.
- Primary rendering bypasses the normal graphics-placement and mouse-shape path.

These are source-level findings, not Cooper PTY reproductions. Existing Vaxis
tests cover several text append and width-change cases, not all these paths.
Neither turning on `PrimaryScreen` nor making a shorter Root establishes the
contract below.

## Decision

### One App configuration, four modes

Add `cooper/screen` for Ard-native screen configuration. The following is the
accepted public declaration surface; bodies are omitted:

```ard
enum Mode {
  alt,
  main,
  inline,
  split,
}

struct Config {
  mode: Mode,
  height: Int?,
  clear_on_exit: Bool,
}

fn config(mode: Mode, height: Int?, clear_on_exit: Bool?) Config
```

Screen configuration stays in `cooper/screen`; the root module does not re-export
its types or constructor. The existing App constructor gains an optional argument:

```ard
fn app(
  exit_on_ctrl_c: Bool?,
  auto_focus: Bool?,
  use_mouse: Bool?,
  screen: screen::Config?,
) App!Error
```

For example:

```ard
use cooper
use cooper/screen

let application = cooper::app(
  screen: screen::config(screen::Mode::split, height: 6),
).expect("create app")
defer application.destroy()
// Construct the ordinary retained tree or mount a CUI view, then run the App.
```

Omitting `screen` preserves existing alternate-screen behavior. `config` creates
open value data and validates it; `app` validates again before acquiring terminal
resources so a manually constructed Config follows the same rules:

| Mode | Height argument | Default `clear_on_exit` |
| --- | --- | --- |
| `alt` | Absent | `true`; `false` is invalid |
| `main` | Absent | `true` |
| `inline` | Required, positive Int | `false` |
| `split` | Required, positive Int | `true` |

Invalid combinations panic. A configured height above terminal height is valid
and clamped at presentation time. Actual terminal acquisition and positioning
failures return Error. Mode, requested height, and exit policy are fixed for one
App lifetime; mode switching, height setters, and content-driven height are not
part of the initial API.

### Surface placement and output ownership

All surfaces span terminal width. Full-height modes use terminal height;
bounded modes use `min(requested_height, terminal_height)`. Zero-sized terminal
reports defer painting and position-dependent operations until usable dimensions
return; they do not discard the requested height or pending output.

| Mode | Placement and ownership |
| --- | --- |
| `alt` | Existing separate-buffer fullscreen session. Exit restores the prior main screen. |
| `main` | Reserve a full-height surface in the normal buffer, scrolling preceding output into history rather than clearing it. There is no independent output pane. |
| `inline` | Begin on a fresh line at the current output position. To append output, remove only the live block, emit output, and repaint the block after it. No persistent upper scrolling region. |
| `split` | Begin after existing output. Managed output advances the footer until its lower edge reaches the terminal bottom. Thereafter output scrolls above the footer while its placement remains fixed. |

Inline and split-footer can look identical before reaching the bottom. Their
contracts differ in output handling: inline replaces a trailing live block;
split-footer maintains a separate scrolling output area and retained footer.
Neither mode follows arbitrary cursor movement by another writer while active.
Only Cooper-managed output participates in this contract.

New normal-buffer surfaces preserve a partial preceding line by moving to the
next line, not by returning to column zero and overwriting it. Already being at
column zero does not require an extra blank line. Reservation may scroll older
rows out of view but must not explicitly erase scrollback. History retention
still depends on the terminal's own scrollback capacity and reflow behavior.

The backend must establish a reliable region origin before painting, accepting
mouse input, or placing a hardware cursor. An unsupported or timed-out position
query must not silently fall back to row zero and erase surrounding output. If
safe positioning cannot be established, startup or resume fails with Error and
restores the previously released terminal state. Exact query/fallback mechanics
belong in Vaxis and require backend tests, not guessed offsets in Cooper.

When a split footer occupies the entire terminal height, no output area is
visible. Managed output must still be committed to terminal history before the
full-height footer is restored. Do not drop output or emit an invalid zero-row
scroll region. This boundary needs a dedicated backend test.

### Managed output, not process-wide capture

Add one Runtime capability for both bounded modes:

```ard
impl Runtime {
  fn mut append_output(text: Str) Bool
}
```

Each call appends a complete plain-text block above the live UI, not a retained
Node. Preserve LF, normalize CRLF to LF, replace other C0/C1 controls and DEL
with spaces, and terminate a nonempty block with LF if it lacks one. An empty
block is a no-op. In particular, ANSI escapes and bare carriage returns are not
terminal commands; this is not a raw-byte or progress-line rewriting API.

The method is background-safe, with whole calls ordered by Runtime acceptance.
It returns true when an active inline/split-footer App accepts the block for
presentation. Acceptance requests a frame even when the retained tree has not
changed. It returns false before start, while suspended, while stopping, after
destruction, or in either full-height mode. False does not print to a fallback
stream. True is not an acknowledgement from the terminal or a guarantee against
process failure.

Runtime serializes acceptance against suspend and destroy. Graceful suspension
and destruction drain accepted output before releasing the surface; later calls
return false. Resize processes accepted blocks in order at the presentation
width, without duplicating them. Retained UI cells are not themselves appended
as output on every frame.

Cooper does not replace process stdout/stderr or intercept file descriptors.
Applications must route active-session logs through this capability; unrelated
writes can invalidate positioning in any normal-buffer mode. While suspended,
applications may use ordinary terminal output or run another foreground program.
This explicit capability differs from OpenTUI's configured `stdout.write`
interception, which itself does not capture stderr or bypass writes.

Raw ANSI streams, structured scrollback surfaces, automatic stdout capture, and
an unmanaged split-footer passthrough variant are deferred. They are not needed
to establish the selected split-footer rendering behavior.

### Coordinates, controls, input, and resize

Root always fills the selected surface. `Geometry.screen`, paint-buffer cursor
coordinates, and public mouse global coordinates are surface-relative, not
physical terminal coordinates. Fullscreen callers see no coordinate change.
Popups, clipping, scrollbars, selections, and focus reveal use the surface bounds.
Imperative controls and CUI components share this contract without mode-specific
constructors or component lifetimes.

At the backend boundary, cursor and image placement add the surface origin;
incoming terminal mouse coordinates subtract it. Events outside the surface must
not acquire new control targets or trigger the existing focused-control scroll
fallback. Preserve movement and release processing for existing pointer capture
and selection so a drag begun inside can finish outside. Reconcile hover using
Cooper's existing capture rules; do not discard outside releases and leave a
pressed control or drag stuck. Mouse-shape updates must work in every mode.
The upper output area is not part of Cooper's retained tree or selectable-text
model. Ignoring its mouse events does not promise native terminal selection
while terminal-wide mouse reporting is enabled.

Raw keyboard input, paste, terminal focus, clipboard, and existing `use_mouse`,
`auto_focus`, and Ctrl+C policies remain App-wide. Partial rendering does not
share input with a concurrently active shell. `suspend()` is the ownership
handoff, not a visual mode change.

Resize keeps configured mode and height, applies physical dimensions, reconciles
the old occupied region, then lays out and paints the new surface. Growing a
clamped region must not treat the larger new height as the old occupied height.
Width reflow, visible input cursors, and placement scrolling can all move the
region: origin updates, painting, and mouse translation must remain consistent.
Do not turn stale queued mouse coordinates into clicks at a new origin.

### Lifecycle and cleanup

Construction retains Cooper's current terminal-acquisition timing; screen
configuration does not defer raw-input ownership until `start`. In the new
normal-buffer modes, reservation and the initial retained frame happen at start.
Destroying an unstarted App restores terminal modes without inventing a live
region or printing blank UI rows. Alternate-screen entry retains its current
construction-time behavior.

`start`, `wait`, `run`, `destroy`, cancellation, and retained ownership keep their
existing contracts. Shutdown is idempotent and drains accepted output before
clearing or preserving the last presented surface:

- Alternate-screen exits its buffer exactly as today.
- With `clear_on_exit: true`, erase only the owned live surface, leaving committed
  output and preceding history intact. Put the cursor at the released surface's
  beginning for the caller's next output.
- With `clear_on_exit: false`, retain the final text cells and put the cursor at
  column zero on the following line, scrolling if necessary. Preservation is
  not a promise that backend graphics survive cleanup; image resources are still
  released as in current Cooper.

In all cases restore terminal modes, scrolling margins, cursor visibility/style,
and mouse state. Existing progress, clipboard, graphics, and signal cleanup
remain serialized with terminal release.

Suspend uses the same clear/preserve policy for the current live surface, drains
accepted output, and releases input. Retained controls, focus, selection, model
updates, and Runtime identity survive. In normal-buffer modes, resume reserves
a new surface after intervening output and repaints the same tree. It never
assumes that the old rows are still available. With preservation enabled this
can leave a previous UI snapshot in history; that is intentional.

Destroying a suspended App must not reacquire and erase a stale normal-buffer
surface. Any backend reacquisition needed to close resources must be detached
from surface reservation or repaint. Failed resume leaves the App suspended;
existing retry/error reporting must not duplicate output or cleanup.

### Implementation boundary and delivery order

1. Add focused failing Vaxis tests for visible cursor/repaint, region growth,
   initial mid-line placement, and suspend/external-output/resume. Implement
   primary-region anchoring, bounded erase, and correct release/reacquisition
   before adding Cooper's public switch.
2. Extend Vaxis with full-height normal-buffer and split-footer presentation,
   output insertion, clear/preserve cleanup, resize-aware origin handling, and
   consistent cursor, mouse-shape, and graphics behavior. Backend operations must
   expose sufficient origin information for Cooper to translate input atomically
   or return already surface-relative events; do not expose speculative Go APIs
   in Cooper's public contract.
3. Implement screen values, validation, output normalization/scheduling, and
   lifecycle policy in Ard. Extend Runtime's existing terminal-I/O serialization,
   not a second terminal writer. Vaxis owns terminal protocol mechanics; no new
   Go framework layer or direct stdout escape-sequence path belongs in Cooper.
4. Integrate a tested Vaxis revision, expose the optional App configuration, and
   add mode examples and documentation. Do not ship a supported mode with silent
   cursor, mouse, or graphics omissions.

Vaxis is a separate repository. Its fixes require a reviewable backend change
and dependency update, not modifications to the local Go module cache. No push,
release, or shared-state operation is authorized by this specification.

### Verification requirements

Extend `testing::new` with the same optional screen configuration; its width and
height describe the simulated terminal, while its frame describes the rendering
surface. Existing calls retain their meaning. Add `TestApp.output_blocks()` as
an ordered recorder of normalized committed blocks, readable after destruction.
The headless driver uses a deterministic origin and does not claim to simulate
terminal scrollback.

Headless tests must cover validation, bounded/full-height geometry, clamp then
grow, overlays and focus reveal at surface boundaries, unchanged component
identity across resize/resume, output sanitization/order, lifecycle rejection,
and draining on suspend/destroy. Keep physical-origin and terminal-history tests
at the Vaxis/PTY boundary rather than deriving expectations from layout code.

PTY tests must pre-seed distinguishable shell lines and exercise:

- Each mode starting below existing output and after a partial line.
- Repeated input-cursor paints at nonzero origins, not just hidden-cursor text.
- Mouse targeting inside, above, and below a live region, including outside
  release and placement changes between receipt and dispatch.
- Terminal width shrink/reflow and height shrink/grow with asymmetric old/new
  region sizes; preceding output must survive.
- Enough appended output to fill the viewport and pin a footer; every output
  block appears once and old UI frames do not leak into history.
- A footer equal to terminal height, including one-row terminals.
- Clear and preserve policies, clean prompt placement, pre-start destruction,
  normal shutdown, Ctrl+C/signals, repeated cleanup, and terminal-mode restoration.
- Suspend, intervening external output, resume, and destruction while suspended.
- Native image placement/cleanup and mouse-shape updates at nonzero origins.
- Existing alternate-screen lifecycle and component examples as regressions.

The current `examples/test_harness.py` Screen is insufficient for history
assertions: it lacks scrolling/history, relevant relative cursor operations, and
accurate erase behavior. Extend the terminal model or use a suitable existing
emulator before claiming preservation from PTY snapshots. Raw byte checks remain
useful for mode restoration, but cannot prove correct rendered-region ownership.
Inspect representative rendered terminal captures as well as assertions.

## Consequences

- Applications choose terminal ownership without changing their controls or
  declarative component tree. Fullscreen remains the compatible default.
- Inline and split-footer share a bounded surface API but keep different output
  ownership contracts. Main-screen remains explicitly full-height.
- Explicit managed output avoids pretending arbitrary process writes are safe;
  it requires applications to route active-session logs through Runtime.
- Main-screen and split-footer clear by default; inline preserves final text.
  Normal-buffer resume starts fresh rather than risking intervening output.
- The feature requires backend fixes and stronger terminal tests before it can
  be presented as interactive-control-compatible, not just text-only rendering.

## Related

- [ADR 0002: Application API](./0002-define-application-api.md)
- [ADR 0013: Runtime ownership](./0013-consolidate-context-into-runtime.md)
- [ADR 0015: Package entry points](./0015-define-package-entry-points-and-ui-namespace.md)
- [ADR 0022: Declarative components](./0022-define-declarative-components.md)
- [Vaxis primary options, sizing, and output](https://github.com/akonwi/vaxis/blob/34e5202041359d6d662fec66791dbcbfe07daa60/vaxis.go)
- [Vaxis cursor flush](https://github.com/akonwi/vaxis/blob/34e5202041359d6d662fec66791dbcbfe07daa60/writer.go#L184-L212)
- [Vaxis primary-screen tests](https://github.com/akonwi/vaxis/blob/34e5202041359d6d662fec66791dbcbfe07daa60/primary_screen_external_test.go)
- [OpenTUI renderer modes](https://github.com/anomalyco/opentui/blob/5eeed22a2f42a842d26c9bd000b06c02d245103c/packages/web/src/content/docs/core-concepts/renderer.mdx)
- [OpenTUI surface geometry](https://github.com/anomalyco/opentui/blob/5eeed22a2f42a842d26c9bd000b06c02d245103c/packages/core/src/lib/render-geometry.ts)
- [OpenTUI split-scrollback offset](https://github.com/anomalyco/opentui/blob/5eeed22a2f42a842d26c9bd000b06c02d245103c/packages/native/src/split-scrollback.zig)
- [OpenTUI native reservation and cleanup](https://github.com/anomalyco/opentui/blob/5eeed22a2f42a842d26c9bd000b06c02d245103c/packages/native/src/renderer.zig)
