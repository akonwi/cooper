# Evaluating an Ard-native layout engine

Evaluation, not an accepted architecture decision. September 9, 2026.

## Recommendation

First strengthen conformance tests for Cooper's complete public layout contract,
independently of whether its solver is ever replaced. The
[public layout audit](./layout-conformance-audit.md) maps the supported vocabulary
to existing evidence, missing cases and unresolved semantics. Tinear is a
real-application integration reference, not the definition of support or the
priority order for this work.

After that coverage is established, evaluate an Ard-native solver with a measured
prototype. Do not replace the production backend yet, narrow the public Style
contract to Tinear's current usage, or translate Yoga wholesale.

The strongest demonstrated benefit is ownership and removal of Tess's native
build dependency, not speed. Cooper already owns almost everything around the
solver. An Ard implementation can remove the second language boundary from
layout, but its performance and complete behavioral compatibility remain
unproven. Tinear makes the evaluation substantially better grounded; it does not
make Flexbox a small algorithm.

Sources inspected:

- Cooper at [the setup commit](https://github.com/akonwi/cooper/commit/a82cd847b955a443843e9d00a163d943232670b6), including ADRs 0001–0015.
- Tinear's default branch at [the inspected revision](https://github.com/akonwi/tinear/commit/389b939604c94964f7a0c1387f6f45e6527d3d19).
  It pins [Cooper's package-entry-point revision](https://github.com/akonwi/cooper/commit/278a8fe8cf7bdc87ae96b6f2f8da6dea20b9a591), already using `cooper` and `cooper/ui`.
- [Tess's pinned source](https://github.com/AnatoleLucet/tess/tree/c76872ba846380681de892662caaca9bdfa0d3bc), including its vendored Yoga implementation.

Tinear was inspected remotely, not built or run. No candidate Ard solver or
language-feasibility prototype was implemented in this evaluation.

## Replace the solver, not the rendering system

The only first-party Tess import is
[`ffi/core/backend/retainedyoga/yoga.go`](../ffi/core/backend/retainedyoga/yoga.go).
Its boundary consists of node creation/destruction, whole-style application,
child insertion/removal, measured-leaf callbacks and dirtiness, root calculation,
and integer local rectangle retrieval.

[`core/node.ard`](../core/node.ard) currently:

- mirrors the retained child tree into Yoga;
- converts Ard enums and lengths into backend values;
- wraps undefined/exactly/at-most measurement modes;
- forces immediate children of a scrolling node to have effective shrink zero;
- synchronizes local rectangles into screen geometry;
- derives content extents from immediate children's local right/bottom edges;
- clamps requested scrolling and translates descendant geometry.

Those last four points are Cooper semantics, not behavior to rediscover by
porting Yoga. Keep scrolling, clipping, focus reveal, hit testing, stacking,
selection, event routing, and post-commit ordering in their current owners.
Private ScrollBox, TextArea, and Select composition must keep working unchanged.

Text segmentation, Unicode wrapping, and terminal width measurement already
exist in Ard-facing controls. The solver must supply the right measurement
constraints, not implement another text layout engine. Text measures unwrapped
when width is undefined, and wraps under finite constraints. Input measures its
value or placeholder plus caret room. TextArea has a measured private viewport
with its own wrapping and caret semantics.

## Tinear provides useful acceptance workloads

| Workload | Features and evidence |
| --- | --- |
| Shell | Full-size column, fixed chrome, growing body, hidden retained screens: [shell controller](https://github.com/akonwi/tinear/blob/389b939604c94964f7a0c1387f6f45e6527d3d19/tui/shell_controller.ard#L137-L190). |
| Inbox | 35% pane plus zero-width growing/shrinking detail, min-width/min-height zero, independent scroll viewports, all rows retained: [construction](https://github.com/akonwi/tinear/blob/389b939604c94964f7a0c1387f6f45e6527d3d19/tui/inbox_controller.ard#L206-L283), [row reconciliation](https://github.com/akonwi/tinear/blob/389b939604c94964f7a0c1387f6f45e6527d3d19/tui/inbox_controller.ard#L400-L435). |
| Board | Computed wide row, horizontal outer scrolling, vertical columns, absolute drag layer and ghost: [retained structure](https://github.com/akonwi/tinear/blob/389b939604c94964f7a0c1387f6f45e6527d3d19/tui/board_controller.ard#L12-L45), [overlay and sizing](https://github.com/akonwi/tinear/blob/389b939604c94964f7a0c1387f6f45e6527d3d19/tui/board_controller.ard#L112-L189). |
| Markdown detail | Full-width, selectable, word-wrapped measured leaves and block margins: [Markdown controller](https://github.com/akonwi/tinear/blob/389b939604c94964f7a0c1387f6f45e6527d3d19/tui/markdown_controller.ard#L130-L207). |
| Modals | Full-screen absolute centering, 70% width capped at 72 cells, 80% max height, rounded border, padding and gap: [modal host](https://github.com/akonwi/tinear/blob/389b939604c94964f7a0c1387f6f45e6527d3d19/tui/modal_host.ard#L25-L73). |
| Toasts | Right/bottom anchoring, end alignment, fit-content capped at 46 cells, explicit terminal-text measurement: [toast host](https://github.com/akonwi/tinear/blob/389b939604c94964f7a0c1387f6f45e6527d3d19/tui/toast_host.ard#L35-L79). |

Tinear has resize tests at 60×20, 100×30, and 160×40. Its live PTY test resizes
100×24 → 60×20 → 100×24 and exercises scrolling. Its documented validation is
`ard check main.ard`, `ard build main.ard --out ard-out/tinear`, `ard test`,
`go test ./...`, and `python3 test/pty/test_tinear.py`.

No explicit flex-basis, flex-wrap, or virtualized-list implementation was found
in Tinear. That is an observation about this consumer, not evidence that those
features are unsupported by Cooper. In particular, the existing virtual-list
benchmark is not a substitute for Tinear's fully retained Inbox workload.

## Compatibility is wider than the consumer's current needs

[`ui/style.ard`](../ui/style.ard) exposes reverse directions, wrapping and
wrap-reverse, relative/static/absolute positioning, display-contents, auto
margins, percentages, min/max constraints, flex basis, baseline alignment, and
max-content/fit-content/stretch lengths. The layout playground already exercises
wrapping and reversed rows even though Tinear does not.

Characterize these before deciding to preserve, change, or reject any of them.
The current style-vocabulary test largely checks stored values; it does not
establish the resulting geometry for every enum and combination. Targeted
coverage for contents flattening, baseline behavior, intrinsic constraints,
fractional distribution, and their interactions is insufficient for a solver
replacement. Passing the current suite is necessary, not sufficient.

Important inherited behavior and compatibility traps:

- **Cooper defaults are authoritative.** It applies column layout, relative
  positioning, shrink 1, grow 0, and stretch alignment. Do not copy Tess's initial
  row/static defaults. Some unexposed Yoga defaults still matter, particularly
  web-default align-content stretch for wrapped lines and border-box sizing.
- **Zero is bounded.** Tess treats a zero root dimension as undefined. Cooper
  deliberately works around that with a positive subnormal. The replacement
  needs an explicit undefined constraint, not that workaround.
- **Style replacement clears values.** Cooper sends NaN point values because
  Tess silently ignores undefined in several setters. Native Ard state should
  replace the whole value directly, preserving the observable clearing behavior.
- **Rounding is part of layout.** Yoga's point scale is one; it rounds against
  absolute edges and treats measured text specially to avoid truncation.
  Independent early integer rounding can introduce gaps or change line breaks.
  Preserve fractional intermediate values initially and characterize edge
  snapping before publishing integer rectangles.
- **Flex resolution is iterative.** Weighted shrink depends on basis, and
  min/max clamping requires redistributing remaining space. A single
  proportional division followed by clamping is not sufficient.
- **Measurement depends on sizing mode.** Intrinsic measurement, finite text
  remeasurement, percentage resolution in indefinite parents, overflow sizing,
  and wrapped line cross sizes interact. An unconditional measure-once pass is
  not a sufficient algorithm.
- **Contents and absolute positioning need real semantics.** Layout children
  can differ from retained children; static ancestors affect containing blocks.
  Do not flatten or reparent the actual retained tree to solve layout.
- **Alignment vocabulary needs a decision.** Tess exposes one broad align enum;
  not every value means a meaningful item-alignment mode. No application baseline
  callback is exposed. Probe actual behavior and document it rather than silently
  deleting variants or inventing CSS support.

Tess is a cgo wrapper around native Yoga archives, not a Go or WASM layout engine.
Its vendored Yoga revision is recorded in
[`etc/YOGA_VERSION`](https://github.com/AnatoleLucet/tess/blob/c76872ba846380681de892662caaca9bdfa0d3bc/etc/YOGA_VERSION).
Relevant reference code includes
[`SizingMode.h`](https://github.com/AnatoleLucet/tess/blob/c76872ba846380681de892662caaca9bdfa0d3bc/etc/include/yoga/algorithm/SizingMode.h),
[`PixelGrid.cpp`](https://github.com/AnatoleLucet/tess/blob/c76872ba846380681de892662caaca9bdfa0d3bc/etc/include/yoga/algorithm/PixelGrid.cpp),
[`Cache.cpp`](https://github.com/AnatoleLucet/tess/blob/c76872ba846380681de892662caaca9bdfa0d3bc/etc/include/yoga/algorithm/Cache.cpp), and
[`LayoutableChildren.h`](https://github.com/AnatoleLucet/tess/blob/c76872ba846380681de892662caaca9bdfa0d3bc/etc/include/yoga/node/LayoutableChildren.h).

## Proposed implementation boundary

Start with an unsupported `core/layout.ard` module using Ard Style values and
typed measurement inputs/results, with no imports of either public facade.
It owns layout-only state: sizing constraints, measured-leaf callback, cached
results, dirtiness, and local rectangles. Core Node remains the authority for
retained identity, child mutations, attachment and Runtime ownership.

A one-to-one layout node replacing the current Yoga handle is the smallest
initial integration: it permits isolated solver tests and temporary reference
comparison without giving the solver focus, event, paint, or lifecycle duties.
Keep tree synchronization in the existing Node add/remove paths. Do not expose
public backend selection, introduce a general plugin interface, or reconstruct
the entire tree every frame. Reassess duplicated topology after parity, not
during the behavior migration.

Suggested algorithm stages are constraint resolution and intrinsic sizing,
flex-line collection, bounded grow/shrink redistribution, final constrained leaf
measurement and line sizing, alignment/positioning, absolute descendants, and
terminal-cell edge snapping. These are responsibilities, not a promise that
each can be implemented as one traversal.

Begin with exact constraint-key measurement caching and ancestor dirtiness.
Yoga's broader compatible-constraint reuse can wait until profiles justify it.
Never reuse measurements solely by node identity: content revisions, wrapping,
constraints and terminal-width policy can change the result. Paint-only changes
must not eventually force all text to be remeasured.

No obvious language capability is missing: the existing framework already uses
mutable retained references, enum-based styles, recursive traversal, callbacks,
and floating-point values. That is architectural evidence, not compiler or
performance proof. Before adopting a new representation, consult `ard-expert`
and compile the smallest recursive-state/callback/cache shape with the pinned
compiler, as required by repository guidance.

## Measured baseline and its limits

Executed in this Linux x64 orb with Go 1.27.0 and the CI-pinned Ard compiler:

```sh
python3 benchmarks/run.py --iterations 25 --warmups 3
```

Selected results, median / p95 in microseconds:

| Existing metric | Median | p95 |
| --- | ---: | ---: |
| 1,001-node construction | 18,555 | 21,879 |
| 1,001-node initial layout | 46,177 | 68,301 |
| 1,001-node single update | 20,081 | 37,290 |
| 1,001-node resize | 8,222 | 10,693 |
| Virtual-list initial layout | 466 | 575 |
| Virtual-list single-row update | 472 | 561 |
| Virtual-list window-shift average | 539 | 644 |
| Virtual-list resize | 779 | 1,133 |
| 1,000 attach/detach/render cycles | 189,743 | 213,783 |
| Deep-tree initial layout | 305 | 910 |

The benchmark completed successfully. These are **not isolated Yoga timings**:
`application.render()` calls runtime draw, which includes layout, geometry,
focus/selection reconciliation, buffer allocation and painting. The large-node
case starts with an 80×1,000-cell frame. The virtual-list node count is the
benchmark's own label and omits some private composition. Orb noise and GC also
limit comparisons. No Ard speedup can be inferred from this data.

`go list -deps` found Tess as the only non-runtime package with CgoFiles in
Cooper's current Go dependency graph. Removing it is therefore a concrete route
toward cgo-free Cooper builds, but that must be verified after replacement; it
does not establish cgo-free builds for Tinear or eliminate Vaxis/other Go interop.

The existing layout-playground PTY test also passed, covering row/column flow,
wrapping, centering, spacing, reverse flow, overlays, resize and clean exit.
No application visual changes were made.

## Stages and go/no-go criteria

1. **Establish public conformance before refactoring.** Add independent behavioral
   assertions to Cooper's existing test suites. Cover odd sizes, zero and
   indefinite bounds, asymmetric padding/margins, auto margins, min/max freezes,
   reverse/wrapped lines, contents, absolute containing blocks and style resets.
   Resolve ambiguous public semantics instead of treating current backend output
   as automatically correct. Include mutation sequences and fresh-tree equivalents.
   A backend-neutral comparison format can follow if the port needs one; it is
   not a prerequisite for thorough public tests.
2. **Prototype the hardest common path.** Implement row/column flex with bounded
   growth/shrink, percentages, min/max, wrapped measured text and deterministic
   snapping. Run a Tinear-shaped split pane and capped modal/toast. Separately
   time layout-only work, measurement calls, allocations, unchanged passes,
   single-leaf changes and resizing; do not use fixed-size box allocation alone
   to declare feasibility.
3. **Complete the existing Style contract.** Add remaining supported cases and
   private-control composition. Use seeded valid-tree differential tests against
   Tess plus independent arithmetic expectations. For example, 80/40 bases in a
   100-cell row distinguish weighted shrink from equal shrink; adding a 75-cell
   minimum to the first child distinguishes redistribution from final clamping.
   Test rounding at adjacent widths, and zero separately from undefined.
4. **Validate the real consumer.** In an isolated Tinear checkout, substitute the
   candidate Cooper dependency and run its controller/headless and PTY tests.
   Add odd terminal widths and large fully mounted lists to its existing resize
   matrix. Check full cells, local/screen geometry, scroll ranges, selection and
   cursor behavior—not just whether expected labels remain on screen. Inspect
   representative rendered Inbox, Board, modal, toast and Markdown states.
5. **Switch only after parity and performance evidence.** Run all Cooper Ard/Go
   tests, all example PTYs and benchmarks against the candidate. Require no
   unexplained cell/geometry differences in supported behavior, no pathological
   remeasurement on unchanged or small-update passes, and an agreed frame budget
   on fixed hardware. Set numeric limits from isolated and real-app baselines
   before comparing candidates; this orb run does not establish a universal
   threshold. Document intentional semantic changes in a new ADR.
6. **Remove the native dependency.** Delete the Yoga bridge and integer enum
   adapters, remove Tess from module dependencies, and validate no-cgo builds on
   supported targets. Retain regression fixtures; remove temporary production
   backend switching. Revisit caching only with measured evidence.

The immediate priority is stage 1, regardless of the port. This evaluation does
not yet justify a performance claim, a delivery estimate, or changing the default backend. If
measurement/reflow semantics or Ard allocation costs make the prototype
uncompetitive, keep Tess while resolving that specific problem rather than
shipping a reduced-layout substitute.
