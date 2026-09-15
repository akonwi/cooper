# 0021: Define Spring Animations

## Status

Accepted. Supersedes the spring deferral in
[ADR 0014](./0014-define-animation-timelines.md); its Timeline API remains unchanged.

## Context

ADR 0014 introduced Runtime-owned, demand-driven animation timelines with fixed
durations and progress-based easing. Elastic easing can look like a spring, but
it does not retain velocity when an application changes the target mid-flight.
Interactive motion needs a scalar value with momentum and a target, with
completion based on settling rather than a prescribed duration.

Harmonica provides a small closed-form damped-spring solver. It leaves position,
velocity, targets, scheduling, validation, and completion to the caller. Its
algorithm fits Cooper, but adding a Go physics backend would expand the interop
boundary for behavior that can live in Ard. Cooper can port the equations while
retaining its existing Runtime ownership and event-thread mutation rules.

## Decision

### Public model

`Runtime.spring(value, update, options?, on_complete?)` creates a paused
`animation::Spring` owned by that Runtime. It is independent of Timeline:
springs have targets and momentum, not fixed durations or normalized progress.
`animation.ard` exposes Spring, SpringConfig, SpringFrame, and `spring_config`;
the Ard implementation lives beneath `animation/spring.ard`.

`spring_config` returns open configuration data, validated when creating a spring:

| Field | Default | Contract |
| --- | --- | --- |
| `angular_frequency` | `12.0` | Finite, positive, radians per second |
| `damping_ratio` | `0.7` | Finite, non-negative; below 1 oscillates, 1 is critical, above 1 is overdamped |
| `position_tolerance` | `0.001` | Finite, positive, in the animated value's units |
| `velocity_tolerance` | `0.001` | Finite, positive, in value units per second |

Initial value and target must be finite. Invalid contracts and arithmetic outside
the representable Float64 range panic. Zero frequency is rejected rather than
inheriting Harmonica's frozen-state behavior. Zero damping is allowed and may
keep the frame driver active indefinitely.

- `set_target(value)` returns true for a changed target and starts or resumes
  playback, preserving the current floating-point value and velocity. Setting
  the same target is a no-op, including while paused or completed.
- `pause()` freezes value and velocity. `play()` resumes a paused spring;
  playing or completed springs return false. A completed spring is reused by
  setting a different target.
- `value()`, `velocity()`, `target()`, `is_playing()`, and `is_complete()` expose
  current state. `destroy()` is idempotent and releases callbacks. Further
  playback or target mutations panic after destruction.
- `update` receives `SpringFrame { value, velocity, target, delta }`, with delta
  in milliseconds. Round only when applying cell geometry, never in spring state.
- Once both absolute position error and absolute velocity meet their tolerances,
  Cooper snaps to `(target, 0)`, delivers that final update, marks completion,
  and calls `on_complete` once. Position alone is insufficient at a target
  crossing; velocity alone is insufficient at an oscillation's turning point.
- Retargeting, pausing, destroying, or suspending from an update invalidates
  pending completion. A paused/suspended final update can be delivered again
  after resumption before completion. Completion callbacks may retarget safely.

### Ard-owned solver and Runtime scheduling

The solver is an altered Ard port of Harmonica v0.2.0's closed-form damped
oscillator, retaining Charmbracelet's MIT and Ryan Juckett's notices. It uses
the actual elapsed delta in seconds, recomputing coefficients per step. The
overdamped branch uses a cancellation-resistant root and `Expm1` for differences
of nearby exponentials. There is no new Go package dependency or physics engine.

The target is constant over each evaluated frame interval. Large deltas advance
directly to their analytic endpoint, without replaying intermediate oscillations
or clamping elapsed time. Starting/resuming a spring establishes its baseline
on the first delivered frame (`delta = 0`), even if other animations are already
active. App suspension freezes time through the shared Runtime clock reset.

Springs and timelines share the existing demand-driven scheduler. Callbacks run
on the UI thread; background fibers must dispatch mutations. Springs created
inside animation callbacks wait until the next frame. The driver returns to
idle only when neither timelines nor springs are playing. Runtime destruction
destroys both; applications destroying controls earlier must destroy their
associated animations first.

### Testing

Headless coverage includes independently integrated ODE reference trajectories,
all damping regimes and near-critical values, irregular elapsed steps,
nonzero-velocity retargeting, both settling conditions, callback mutation,
Runtime isolation, suspension, and cleanup. The spring lab's PTY test
exercises in-flight retargeting, pause/resume, visible overshoot, exact settling,
reuse, and clean quit.

## Consequences

- Applications gain interruptible, momentum-preserving scalar motion without
  changing Timeline's fixed-duration sequencing contract.
- Framework behavior remains in Ard; the port retains upstream attribution and
  Cooper owns numerical and lifecycle coverage rather than relying on upstream
  spring tests.
- Settling tolerances are expressed in the animated value's units. Applications
  must choose suitable tolerances and keep terminal-cell rounding out of the
  spring state.
- Undamped motion can keep rendering active indefinitely. General physics,
  spring/timeline composition, and automatic Style interpolation remain outside
  this decision.

## Related

- [ADR 0014: Define animation timelines](./0014-define-animation-timelines.md) — spring deferral superseded; scheduler and Timeline contracts retained.
- [ADR 0013: Consolidate Context into Runtime](./0013-consolidate-context-into-runtime.md)
- [Spring lab and comparison recording](../../examples/README.md#spring-comparisons)
- [Harmonica v0.2.0 spring solver](https://github.com/charmbracelet/harmonica/blob/v0.2.0/spring.go)
- [Ryan Juckett: Damped Springs](https://www.ryanjuckett.com/damped-springs/)
