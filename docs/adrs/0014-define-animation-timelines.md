# ADR 0014: Define animation timelines

## Status

Accepted

## Context

ADR 0002 established Cooper as a demand-driven retained renderer and deferred
continuous rendering, frame-rate controls, and animation. Applications now need
a way to animate retained controls without moving mutations onto a background
fiber or forcing every application to build its own frame scheduler.

OpenTUI v0.5.10 provides useful lineage: its `Timeline` schedules numeric
property interpolation and callbacks, while one engine requests continuous
renderer frames only while registered timelines are active. The engine advances
timelines from renderer frame deltas and returns the renderer to demand-driven
operation after the last timeline stops.

OpenTUI's JavaScript-facing details do not fit Cooper directly. It discovers and
mutates numeric object properties through dynamic keys, uses one process-global
engine, permits several invalid or ambiguous timing shapes, and requires manual
engine registration cleanup. Cooper needs an Ard-native typed API, one owner per
Runtime, deterministic headless time, and the same lifecycle guarantees as the
rest of the retained framework.

The earlier vaxis/ui layer provides a second useful reference. Its App-scoped
`AnimationController` exposes typed `0...1` progress, a custom curve function,
a scalar tween, automatic State disposal, and a coalescing 60 Hz
`FrameScheduler`. It is lifecycle-safe but deliberately smaller than a timeline:
it has no sequencing, callbacks, loops, or true pause/resume, and every tick
rebuilds declarative State. Cooper retains its Runtime ownership, curve, scalar
progress, and frame-pacing lessons without restoring the widget/State model.

## Decision

### Public model

Cooper adds a root `animation.ard` module. `Runtime` creates timelines bound to
its own lifetime:

```ard
use cooper/animation

let timeline = application.context.timeline(
  duration: 600,
  loop: false,
  alternate: false,
)

timeline.add(
  duration: 600,
  ease: animation::out_quad,
  update: fn(frame: animation::Frame) {
    let applied = mut panel.style()
    applied.left = style::cells(
      animation::lerp_int(0, 30, frame.progress),
    )
    panel.set_style(applied.@)
  },
)

timeline.call(fn() {
  status.set_content("Complete")
}, at: 600)

timeline.play()
defer timeline.destroy()
```

A timeline is a copyable facade over one shared identity. It starts paused.
`play`, `pause`, and `restart` report whether they changed state. `destroy` is
idempotent. Runtime destruction destroys every remaining timeline.

`Frame` exposes the timing data needed by a typed update closure:

```ard
struct Frame {
  progress: Float64,
  linear_progress: Float64,
  elapsed: Int,
  delta: Int,
  iteration: Int,
}

type Easing = fn(Float64) Float64
```

Cooper provides named easing functions corresponding to the useful OpenTUI
set: linear, quadratic, exponential, sine, circular, bounce, elastic, and back
variants. Easing input is clamped to `0...1`; easing output may overshoot for
back and elastic curves. Applications may supply a custom easing function.

`animation::lerp` and `animation::lerp_int` provide scalar interpolation.
`lerp_int` preserves exact endpoints, accepts intermediate values only within
the exact Float64 integer range, and defines one consistent rounding policy for cell geometry. Specialized
Style, Length, edge, and Color transitions are deferred until repeated use
shows a stable supported shape.

### Timeline behavior

A timeline has a positive duration in milliseconds. Track durations and start
offsets are non-negative and must fit within the timeline cutoff. Invalid timing
is a programmer contract violation and panics when the track is added.

`add` schedules an update closure at an integer millisecond offset. `call`
schedules a callback at an integer offset. Both configure a paused timeline
before its first playback; structural mutation after playback begins is rejected.
Tracks receive eased and linear progress and apply explicit values through retained control setters.
`Frame.delta` is the time advanced in that evaluated timeline segment, not a
license to integrate the same wall-clock delta across skipped iterations. Cooper
does not inspect controls, capture properties by name, or mutate dynamic target maps.

A non-looping timeline reaches its exact final values before completing. A
looping timeline resets scheduled callback and track state for each iteration.
`alternate` reverses progress on odd iterations. Large frame deltas settle the
outgoing endpoint and final relevant iteration without replaying every skipped
intermediate iteration. Scheduled callbacks run at most once in each evaluated
iteration; callbacks belonging only to skipped iterations do not run. Restart or
destruction from an update abandons pending callbacks for that iteration, while
pause/resume preserves a pending track completion.

Nested/synchronized timelines, relative/string time labels, per-track infinite
loops, springs, physics, and dynamically appended tracks are deferred.
Independent timelines and integer offsets cover the initial sequencing model.

### Runtime engine

Every Runtime owns one private animation engine. Cooper does not expose a global
engine and does not expose a general public frame callback as part of this
decision.

```text
Timeline.play
  -> Runtime animation engine becomes active
  -> coalesced frame wake enters the App event loop
  -> engine advances from a monotonic delta
  -> update callbacks mutate retained controls on the UI thread
  -> effective setters coalesce one paint
  -> next frame is scheduled only while a timeline remains active
```

The frame driver is dormant when no timeline is playing. Starting the first
timeline requests frame delivery; stopping or completing the last timeline
returns Cooper to its normal demand-driven behavior. Frame cadence is runtime
policy rather than a Timeline guarantee.

Animation callbacks run synchronously on Cooper's event thread. They follow the
same mutation rule as input listeners and dispatched callbacks. A background
fiber must use `Runtime.dispatch` before controlling a timeline.

Suspending an App freezes timeline time. Resume resets the frame-clock baseline
so suspension does not become one large animation delta. Runtime destruction
stops frame delivery before destroying timelines and retained controls. Owners
that destroy controls earlier must destroy their timelines first.

### Testing

Headless Runtime time remains deterministic. `TestApp.advance_time(milliseconds)`
advances the monotonic test clock and active timelines without sleeping. Tests
can assert intermediate values, easing, sequencing, looping, alternate progress,
completion, pause/restart, suspension, timeline destruction, and Runtime
cleanup.

PTY coverage verifies paced live frame delivery, final retained output, and
clean terminal restoration. Exact easing, completion, and return-to-idle engine
state remain deterministic headless tests.

## Consequences

- Cooper gains animation without abandoning its demand-driven renderer.
- Application animation code stays typed and explicit, but is more verbose than
  OpenTUI's dynamic property map.
- One Runtime owns scheduling and cleanup, so multiple Apps and TestApps do not
  share global animation state.
- Update closures can animate multiple related values atomically and can target
  application state as well as controls.
- Layout animation may run layout and paint every frame; applications remain
  responsible for choosing restrained durations and workloads.
- The initial API favors predictable scalar timelines over nested composition,
  physics, and broad automatic Style interpolation.

## Related

- [ADR 0002: Define the application API](./0002-define-application-api.md)
- [ADR 0013: Consolidate Context into Runtime](./0013-consolidate-context-into-runtime.md)
- [OpenTUI animation documentation](https://opentui.com/docs/application-apis/animation)
- [OpenTUI v0.5.10 Timeline source](https://github.com/anomalyco/opentui/blob/f6673a04ccb671b9207da358c57152bfd27c781f/packages/core/src/animation/Timeline.ts)
- [vaxis/ui AnimationController source](https://github.com/rockorager/vaxis/blob/8a93a9a0e2e7/ui/animation.go)
- [vaxis/ui FrameScheduler source](https://github.com/rockorager/vaxis/blob/8a93a9a0e2e7/ui/frame_scheduler.go)
