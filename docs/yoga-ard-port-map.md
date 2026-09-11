# Tess replacement: Yoga-to-Ard port map

September 11, 2026. Implementation direction, not a claim of completed parity.

The goal is to replace Tess, including its Yoga dependency, with Ard-native
layout machinery. Translating Yoga's algorithms is how we replace the solver
inside that dependency chain; leaving Tess in place is not completion.
The current `core/layout.ard` is an independently implemented
solver. Its tests and retained-framework improvements remain useful, but adding
a custom cache to that solver would not make it a Yoga port.

Cooper currently declares Tess in `go.mod`, and its retained Yoga bridge imports
Tess for node construction, style application, measurement callbacks, tree
operations and layout results. The replacement must own those capabilities in
Ard as well as the solver. It need not reproduce Tess's Go API or expose Tess
features Cooper does not publicly support. The final dependency graph must have
no Tess module, Yoga native archive or layout-specific CGo bridge. This does not
remove Cooper's separate Vaxis dependency or promise a Go-free application.

## Source and configuration

Translate the Yoga tree bundled by
[Tess c76872ba846380681de892662caaca9bdfa0d3bc](https://github.com/AnatoleLucet/tess/tree/c76872ba846380681de892662caaca9bdfa0d3bc/etc/include/yoga).
Its `etc/YOGA_VERSION` identifies Yoga revision `8ba025e`, not Yoga 3.2.1.
Tess's build workflow copies sources and builds a static archive from that
revision; this establishes provenance, not a reproducible archive checksum.

Tess's default configuration enables web defaults. Yoga defaults supply point
scale 1, no errata and no experimental features. Cooper then explicitly applies
its Style values; raw Yoga defaults alone are not the application contract.
Preserve this supported configuration first rather than exposing all Yoga
configuration options through Cooper.

Source paths below are relative to the pinned `etc/include/yoga/` tree.
Keep Meta's copyright and MIT permission notice with translated code and retain
the upstream license text. Cooper's Apache license need not be replaced. If
Tess wrapper code is copied, preserve its license separately too.

## What stays and what is replaced

Keep the public Ard Style and geometry API, validation, measurement callbacks,
Node content rectangles, retained identity and lifecycle, scrolling, focus,
hit testing, painting, and control fixes. Keep public conformance tests,
failing-before regressions, PTY tests and benchmark workloads. Tinear remains
an additional consumer check, not the specification of Cooper's public API.

Replace the independent recursive solver and flex allocation algorithm with
recognizable Yoga phases and state. Keep backend-specific state beneath the
internal layout boundary; applications must not acquire Yoga types or setters.
Use Ard data structures without copying C++ allocation, C ABI or Go finalizers.
Do not retain Tess's zero-to-positive-subnormal workaround: explicit zero and
undefined availability must be distinguishable in the Ard representation.

| Pinned Yoga source | Current Ard counterpart | Port action |
| --- | --- | --- |
| `numeric/Comparison.h`, style length resolvers, `algorithm/BoundAxis.h`, `FlexDirection.h` | `finite_length`, `resolve`, `bounded`, axis helpers | Translate undefined handling, comparisons, bounds and axis rules before the kernel. Preserve Float32 branch behavior first; Float64 is not an Ard requirement. |
| `node/Node.cpp`, `node/LayoutResults.h`, `YGNodeStyle.cpp`, ownership mutations in `YGNode.cpp` | `Node`, `apply`, `insert`, `remove`; direct measure assignment | Add owner links, change-aware invalidation and Yoga layout/cache state. Route callback replacement and content dirtiness through it. |
| `algorithm/CalculateLayout.cpp`: root entry and `calculateLayoutInternal`; `algorithm/Cache.cpp` | `Node.compute`, `compute`; no cross-layout cache | Translate the cache-aware wrapper and distinguish measurement from layout visits. |
| `CalculateLayout.cpp`: measured/empty/fixed-size leaf paths | Early paths in `compute_visible` | Translate fast paths and measurement constraints; retain the fixed-leaf callback regression as evidence. |
| `CalculateLayout.cpp`: child flex basis; `algorithm/FlexLine.cpp` | Natural probes, `Item`, `Line`, inline line packing | Translate basis generation/reuse, available inner dimensions, child traversal and line collection. Replace integer probe modes with explicit sizing concepts. |
| `CalculateLayout.cpp`: two flex passes, main-axis justification | `flex` iterative freezing and inline placement | Translate the two passes faithfully, then isolate the accepted redistribution difference described below. |
| `CalculateLayout.cpp`: stretch, cross alignment, multiline alignment, wrap reversal; `algorithm/Baseline.cpp` | Inline cross-axis logic | Translate phase ordering; substitute Cooper's documented baseline rule explicitly. |
| `algorithm/AbsoluteLayout.cpp` | `Node.absolute` | Translate containing-block traversal and sizing/positioning; preserve public contents and inset tests. |
| `node/LayoutableChildren.h` | `collect` | Align layout traversal with Yoga's contents flattening; retain Cooper's independent retained-tree behavior. |
| `algorithm/PixelGrid.cpp` | `project`, `freeze_horizontal`, `Allocation` | Translate edge projection mechanics, then apply ADR 0020's tie and width-reconciliation rules explicitly. |

The large `compute_visible` function currently combines these responsibilities.
Splitting it mechanically is not sufficient: the translated phase ordering,
conditions and persistent state must be traceable to the source.

## Cache and invalidation are part of the algorithm

Yoga stores an owner and dirty state, computed flex basis and its generation,
layout generation, configuration version, last owner direction, one layout
cache entry, and an eight-entry measurement cache. It distinguishes measured
dimensions from committed layout dimensions. A dirty node in a new generation,
changed configuration, or changed owner direction requires a visit.

`Cache.cpp` does more than compare an exact width/height tuple. Both axes must
be compatible. Cases include matching rounded constraints, an exact constraint
matching the previous measured size, a formerly unconstrained measurement that
fits a new upper bound, and a stricter upper bound still containing the result.
Margins and sizing modes participate. Numeric equality uses Yoga's 0.0001
tolerance and treats two undefined values as equal.

Port these rules together with dirty propagation, not as an isolated memoizer.
Today `apply` assigns values unconditionally, and retained `mark_measure_dirty`
requests a redraw without invalidating layout measurements. Style/border edits,
content changes, measure-function replacement, insertion, removal and
reparenting must invalidate the appropriate owner chains. Detached and newly
attached subtrees need mutation tests too.

ADR 0020's projected-width replay is additional state, not a reusable natural
measurement. Its frozen allocations remain transaction-local. The adaptation
must distinguish replay from ordinary measurement/layout so it cannot poison
Yoga's basis or measurement caches.

## Accepted Cooper rules need explicit adaptations

The accepted ADRs remain in force. A faithful source translation does not imply
silently restoring every pinned Yoga result. Each difference needs a focused
adapter or clearly marked branch, its ADR reference and a distinguishing test.

| Contract | Difference or compatibility question | Treatment |
| --- | --- | --- |
| ADR 0016 intrinsic keywords | Pinned `StyleSizeLength` stores keywords, but its basic resolver resolves only points and percentages. The observed `max_content` Text `abc defgh` in width 5 becomes 5×2, not the accepted 9×1. | Keep intrinsic contributions and finite fit/stretch rules as an explicit extension; a renamed Yoga enum is insufficient. |
| ADR 0016 percentage cycles and constraints | Cooper specifies indefinite intrinsic references, constraint precedence and intrinsic bounds. | Compare each rule to translated Yoga with targeted probes; do not assume source parity from similar terminology. Preserve OR-4 and intrinsic-axis regressions. |
| Flex redistribution | Pinned Yoga explicitly uses exactly two passes and notes it is not the variable-pass CSS algorithm. Current Ard freezes net violations repeatedly. | Translate the source algorithm first. Use cases where the algorithms differ to identify required Cooper adaptations; do not weaken accepted constraint tests to obtain parity. |
| ADR 0017 alignment | Property-specific validation and Cooper defaults belong to the public API. | Keep validation; translate supported alignment and distribution mechanics under explicit Cooper Style values. |
| ADR 0018 baseline | Cooper uses each item's bottom border-box edge, not Yoga's descendant-derived baseline. | Replace the baseline policy explicitly while retaining the translated line/alignment phases. |
| ADR 0019 contents | Boxless layout overlaps Yoga; retained listeners, colors, focus, selection, scrolling and popup lifecycle are framework behavior. | Translate layout traversal, preserve retained changes, and test the integration rather than treating all contents behavior as a solver fork. |
| ADR 0020 rounding | Cooper requires uniform shared-edge rounding with half ties toward positive infinity, without text-specific ceil/floor. | Mark the projection policy difference and test negative ties and measured/unmeasured equivalence. |
| ADR 0020 width replay | Cooper remeasures at projected content width while freezing line membership and horizontal allocation, accepting spare space or overflow. | Keep this as an explicit post-allocation extension; do not repeatedly repack or let replay results enter natural probes. |

Do not rewrite accepted ADRs merely to make the port easier. Any newly discovered
conflict beyond these documented policies must be reported before changing the
public contract. Floating-point precision also needs boundary evidence: compare
Float32 source behavior before assuming the current Float64 implementation is
semantically interchangeable.

## Translation and verification sequence

1. **Establish a differential reference.** Keep the pinned backend available in
   an isolated test checkout. Run identical, supported Style trees against both
   implementations. Record expected ADR differences separately from unexpected
   mismatches; do not add a permanent public backend toggle.
2. **Translate numeric rules and node state.** Implement source-equivalent
   undefined/comparison rules, ownership, dirty propagation and generations.
   Verify mutation and detach/reparent invalidation before caching anything.
3. **Translate the recursive wrapper and leaf paths.** Port layout versus
   measurement visits and cache compatibility together. Assert callback counts
   and independently expected geometry for unchanged layout, changed content,
   exact/at-most/undefined constraints, resize and callback replacement.
4. **Translate the flex kernel.** Port basis, line collection, two-pass flex,
   justification, stretch and multiline alignment in source order. Compare
   asymmetric grow/shrink cases, bounds, margins, gaps and reverse/wrap states.
5. **Translate absolute layout and projection.** Verify containing blocks,
   contents, insets and fractional nested edges. Integrate the documented ADR
   adaptations with explicit divergence tests, including projected-width replay
   under caching and content mutation.
6. **Switch and prove the replacement.** Run all public headless tests, PTYs,
   rendered affected states and the identical-source performance comparisons.
   Compare mutation results with fresh trees and independently calculated
   expectations. Remove the unused Go bridge/Tess dependency only after the
   translated implementation and documented adaptations pass those checks.
   Verify module metadata, source imports and a clean build no longer require
   Tess or its Yoga archive; update layout-specific setup requirements too.

Use reviewable translation stages, preserving source names where useful and
recording source paths next to translated algorithms. Do not prolong two
production solvers or add a generic backend framework for this migration.
Unsupported Yoga capabilities need not become new Cooper features.

Current evidence is a baseline, not completion: 372 passing Ard tests and the
[performance comparison](./layout-performance-comparison.md) characterize the
independent implementation. The unchanged auto-height workload makes 192,000
measurement callbacks versus Yoga's zero across 1,000 layouts. The translation
must eliminate that unnecessary work without hiding stale-layout bugs. Timing,
allocation and real-text costs still require measurement; callback parity alone
does not establish performance parity.

## First translation stage: executable reference and numeric rules

The reference is now reproducible with `python3 test/compare_layout.py` (optional
`--output /tmp/tess-layout-reference.json`). It creates and removes a temporary
worktree at the pinned Cooper/Tess checkpoint, copies the same public-API input
program into it, and builds both programs separately. It requires Ard, Go, Git,
a C++20 compiler and the baseline commit in local Git history. No production
backend selector is involved.

The initial fixture asserts 14 shared rectangles: asymmetric grow/shrink with
bounds, reparented percentages, resize, zero availability, and text content
mutation/unchanged layout/resize with following-sibling geometry. It also checks
the exact ADR 0016 max-content difference: Tess 5×2, candidate 9×1. These are
starter fixtures, not complete differential coverage. The runner checks both
implementations against independently specified rectangles rather than accepting
any matching output. A failure-injection check rejected 35 corrupted reports
(wrong widths, missing/extra observations, and a duplicate name).

`core/layout/numeric.ard` translates the Float32 scalar undefined, defined,
min/max-or-defined and inexact-equality rules from `numeric/Comparison.h`.
The upstream MIT notice is retained. It has no Go interop. Three focused Ard
tests cover undefined versus zero/negative/infinity, both sides of the strict
0.0001 tolerance, asymmetric extrema, and first-operand signed-zero preservation.
The comparison runner also compiles the actual pinned C++ header and compares
169 operand pairs against Ard, including input/output bits for defined floats
and normalized NaNs. All pairs match. JSON evidence includes source/header
hashes and observations.

Verification at this stage: `ard test` **375 passed, 0 failed, 0 panicked**;
all four new Ard files pass `ard check` and `ard format --check`; the differential
runner passes both geometry and numeric comparisons. No production appearance
change was made. The numeric module is not yet wired into the live Float64 /
negative-sentinel solver: that transition belongs with translated node state
and recursion, not an unsafe partial change of numeric representation.

**Next:** translate owner links, dirty propagation and persistent layout state,
then the cache-aware recursion and leaf paths. The independent production
kernel and Tess dependency remain; this stage does not claim a completed port
or a measurement-performance improvement.
