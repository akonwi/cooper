# Tess replacement: Yoga-to-Ard port map

September 12, 2026. Production integration complete for Cooper's supported
configuration and accepted ADR policies. This is not a claim of exhaustive
upstream Yoga conformance. The original plan and incremental proof log below
are historical; the completion section records the final implementation.

The goal is to replace Tess, including its Yoga dependency, with Ard-native
layout machinery. Translating Yoga's algorithms is how we replace the solver
inside that dependency chain; leaving Tess in place is not completion.
The independently implemented solver has been removed. `core/layout.ard` now
owns retained layout data and geometry projection; `core/layout/visitor.ard`
owns the translated recursive algorithm and invokes the focused phase modules.

Cooper no longer declares Tess in either Go module, and the retained Yoga bridge
has been deleted. Ard owns node construction, style application, measurement
callbacks, tree operations and layout results as well as the solver. It does
not reproduce Tess's Go API or expose Tess
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

The table records the original replacement plan, not remaining work.
`compute_visible` and the independent flex solver are gone; source references
and copyright notices accompany the translated phases.

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

## Ownership and dirty propagation stage

Layout nodes now track their owner and dirty state. The clean-to-dirty transition
propagates through owners, following Yoga's `markDirtyAndPropagate`; insertion
invalidates the new owner even when the child is already dirty, and removal
clears the owner link and invalidates the old chain. Repeated removal does
nothing. Change-aware Style application compares layout properties and resolved
border thickness, excluding colors, z-order and border appearance.

Retained `mark_measure_dirty` and measure-callback replacement now invalidate
layout state. The focused test failed before these retained hooks were wired
(`2 passed, 1 failed`, at "Content invalidates layout, not only rendering") and
passes afterward. Its mutable-content fixture uses an explicit shared object,
not a scalar captured by value. Geometry changes from width 3 to 7 and then to
9×2 after callback replacement.

`test/layout_state_test.ard`: **3 passed**. It also checks all 25 compared layout
Style properties, identical replacements, paint-only changes, resolved border
thickness, owner-chain isolation and detach/reparent transitions. Full `ard test`:
**378 passed, 0 failed, 0 panicked**. Compiler/formatter checks, `go test ./...`,
and the geometry/numeric differential runner pass.

This is deliberately not cache reuse yet. The existing full-tree solver clears
dirty state only after completing its transaction. Basis invalidation, cache
entries, generations and visit-local clean transitions must be translated with
Yoga's persistent layout results and recursive wrapper next; no performance
improvement or complete state-machine equivalence is claimed at this stage.

## Cached measurement representation and compatibility stage

`core/layout/cache.ard` now contains Yoga's sizing modes, cached measurement
record/defaults, and two-axis `canUseCachedMeasurement` rules. Compatibility
checks matching constraints, exact measured size after margins, an unconstrained
result that fits a new bound, or a stricter bound still containing the result.
Negative cached dimensions reject reuse; both axes must qualify.

Constraint rounding follows pinned Yoga's scale-one, unforced pixel-grid path,
including its near-half tolerance. It is **not** the ADR 0020 final geometry
projection. The internal flag selects scale-one comparison or unrounded
comparison; arbitrary point scales are not a Cooper capability. Computation is
Ard-native except the existing numeric widening helper, which only converts
Float32 to Float64. No new Go behavior or Tess runtime import was added.

`python3 test/compare_layout.py` now compiles pinned `Cache.cpp`, links Tess's
platform Yoga archive for its configuration/pixel-grid functions, and compares
**5,184 cache decisions and 12 rounded constraints** against Ard. The matrix
varies old/new sizing modes, rounded/unrounded comparison, availability
(including undefined and near-half values), and valid/invalid cached width;
its height is fixed and row margin is two. Separate focused assertions cover
height mismatch, zero margins, exact fits and looser-bound rejection. This is
not exhaustive cache or layout equivalence. Archive and source hashes are
recorded in the JSON evidence.

Verification: `ard test test/layout_cache_test.ard` **2 passed**; full `ard test`
**380 passed, 0 failed, 0 panicked**; all three changed/new Ard files pass compiler
and formatter checks. Existing geometry and numeric comparisons still pass.
No production geometry changed. Persistent cache storage, generations, lookup
ordering and recursive visit integration remain next; the new predicates are
not wired into the independent solver and do not yet reduce measurement calls.

## Persistent cache state and lookup ordering stage

`cache::State` translates generation/configuration/owner-direction tracking,
computed flex basis metadata, one layout record and the searchable measurement
prefix from `LayoutResults` and `calculateLayoutInternal`. Preparation discards
cached records for a dirty node in a new generation, changed configuration, or
changed owner direction. Dirty nodes may reuse measurements within the same
generation; clean nodes may reuse across generations.

Measured leaves prefer the layout record, then the oldest compatible measurement
record. Unmeasured nodes use only the appropriate layout or measurement cache
and require matching constraints and modes, not the more permissive measured-leaf
compatibility rules. Storage preserves Yoga's eight-entry prefix reset, including
the reset triggered by storing a layout miss when the measurement prefix is full.
It is not an LRU cache. The Ard representation discards inactive entries instead
of retaining Yoga's fixed array slots; searchable results and ordering match.

Each layout Node now owns this state. Its clean-to-dirty transition clears the
computed flex basis along the owner chain, and detach resets the child's cache
state. The current solver still runs in full; its recursive calls do not yet
prepare/find/store/complete cache visits. This adds storage and invalidation,
not a cache-performance improvement or full layout-result translation.

Verification: `ard test test/layout_cache_test.ard` **5 passed**;
`ard test test/layout_state_test.ard` **4 passed**; full `ard test` **384 passed,
0 failed, 0 panicked**. All four changed Ard files pass compiler and formatter
checks. The existing geometry, numeric and 5,184 cache-predicate comparisons
against pinned Yoga still pass. The new state transitions are covered by focused
source-derived tests, not an end-to-end cached-layout differential test yet.

Next is translating the recursive visit/measurement boundary and leaf paths,
including committing measured dimensions, clearing dirty state only for layout
visits, and keeping ADR 0020 projected-width replay out of natural measurements.

## Cached leaf visits and measurement kernel stage

`core/layout/measure.ard` translates measured and empty-leaf sizing. Callback
constraints exclude padding/border, max-content axes pass undefined availability,
both exact axes skip the callback, and returned content dimensions become bounded
border-box dimensions. The existing measurement types remain available through
aliases, with no callback conversion wrappers. `Axis.bound` preserves pinned
Yoga's maximum-first early return; the future Cooper constraint-resolution
boundary must normalize conflicting min/max values to maintain ADR 0016's
minimum-wins policy. Existing application behavior remains unchanged.

`Node.calculate_leaf` implements the leaf branch of `calculateLayoutInternal`:
prepare/invalidate, lookup, measure on a miss, store bounded results, update
measured dimensions and generation, and commit layout dimensions/clear dirty
only for layout visits. Cache keys retain outer availability including margins;
the measurement kernel receives margin-subtracted space. The entry uses Cooper's
fixed LTR, scale-one configuration and requires already-resolved axis inputs.

The native reference now calls actual pinned `calculateLayoutInternal` for five
visits: initial measurement, repeated measurement, layout in the same generation,
clean layout in the next generation, and dirty layout after changing content.
Ard and Yoga agree on visit/reuse decisions, dirty flags, callback totals
**1 → 1 → 1 → 1 → 2**, and measured dimensions **11×5 → 17×5** after the edit.
The fixture has asymmetric padding and a two-cell horizontal margin. Focused
tests separately cover all nine width/height sizing-mode combinations, callback
inputs/modes, inset floors and bounded natural size **11×5 → 9×8**.

Verification: `ard test test/layout_measurement_test.ard` **3 passed**;
full `ard test` **386 passed, 0 failed, 0 panicked**. All four changed/new Ard
files pass compiler and formatter checks. The extended differential runner,
`go test ./...`, and Text Gallery PTY check pass.

This leaf visitor is exercised directly, not by the current application's
independent container solver. General container recursion, basis/line/flex
translation and projected-width replay integration remain. Do not claim an
application-level reduction in callbacks or remove Tess based on this isolated
leaf proof. The next stage must translate the caller's axis/basis resolution
and container traversal, rather than insert a raw callback memoizer into the
old solver.

## Resolved-axis constraints stage

`measure::Axis.constrain_max` translates `constrainMaxSizeForMode` after
style resolution: a defined maximum includes margins and changes MaxContent
to FitContent; exact/fit allocations remain smaller when already below it.
Undefined availability is replaced by a defined maximum in those modes too.
`available_inner_dimension` translates `calculateAvailableInnerDimension`:
subtract padding/border after margins, apply maximum then minimum, and preserve
undefined space. Its default upper bound is Float32's largest finite value,
not infinity. Unlike callback `inner_size`, resolved bounds can produce negative
inner space. These internal rules are not new public Style semantics.

The native driver includes the pinned `CalculateLayout.cpp` translation unit
to call its private helpers directly. This also rebuilds the reference leaf
visitor from pinned source rather than taking that visitor from the archive;
remaining native dependencies still link against the archive. The evidence
records both the layout-source and archive hashes.

Proof: **2,016** axis cases match sizing modes and Float32 result bits, spanning
all three modes, undefined/negative/zero/finite/infinite availability, asymmetric
margin/inset values, absent bounds and conflicting bounds. The focused test
independently asserts outer16 − margin3 − inset4 = inner9, min19 overriding
max13 to produce inner15 with inset4, and inner−2 versus callback0.
`ard test test/layout_measurement_test.ard`: **4 passed**;
full `ard test`: **387 passed, 0 failed, 0 panicked**. Compiler and formatter
checks pass for all three changed Ard files. Existing differential cases pass.

These helpers accept already-resolved dimensions and remain outside the active
application solver. Style/percentage resolution, child flex-basis selection and
container recursion are still next; no Tess dependency removal or application
performance improvement is claimed by this checkpoint.

## Length resolution and processed dimensions stage

`core/layout/length.ard` translates `StyleSizeLength::resolve`,
`Node::processDimensions`, and `Node::hasDefiniteLength` for Cooper's validated
border-box lengths. Percentages use the source's Float32 multiplication order
(`value * reference * 0.01f`). Owner zero is definite; owner NaN is indefinite,
including for zero percent. Keywords remain unresolved at this level rather
than acquiring Yoga's finite-measurement fallback as public semantics.

Processed dimensions use the maximum when min/max have the same units and
inexactly equal values. Otherwise they preserve the preferred dimension.
The comparison happens before percentage resolution; values in different units
must not collapse merely because their resolved sizes happen to agree.

Proof: **60** length resolutions/definiteness checks and **1,728** processed
dimension combinations match pinned Yoga. Cases cover all supported units,
zero/fractional/large owner sizes, undefined owner space, and bounds just inside
and outside the source's equality tolerance. Two deterministic tests independently
assert fractional percentages, definite zero, unresolved keywords, unit-sensitive
bound equality and choosing the maximum's exact value. Full `ard test`:
**389 passed, 0 failed, 0 panicked**; targeted tests **2 passed**. Compiler and
formatter checks pass for the three new/changed Ard files in this stage.

The native processed-dimension cases intentionally use fresh nodes. Reusing one
node across the matrix produced 295 mismatches: pinned `StyleValuePool::storeKeyword`
can keep a prior fractional value's indexed flag and store the keyword in the
buffer, while `StyleValueHandle::isKeyword` compares the index itself with the
keyword ordinal. This can corrupt keyword identity after mutation. Fresh-node
cases all match. Ard uses plain length values, not Yoga's packed/indexed storage;
this is not behavior to port, and this proof does not claim storage-mutation
parity. The source locations above record the limitation for future reference.

These are raw resolution primitives, not the complete ADR 0016 sizing policy.
Intrinsic contributions, percentage-cycle policy and min-wins normalization must
be applied explicitly at the caller. Next is child flex-basis selection and its
measurement fallback, followed by container recursion. The active application
solver and Tess dependency remain unchanged.

## Direct flex-basis selection stage

`basis::resolve_without_measurement` translates the first branches of
`computeFlexBasisForChild`: select an explicit resolved basis only when main-axis
available space is defined, otherwise use the processed definite main dimension.
Both preserve the padding/border floor. With experimental WebFlexBasis disabled,
an existing explicit basis survives a new generation; definite dimensions instead
recompute it. Dirty invalidation permits the explicit basis to be recalculated.
Zero availability is defined; owner size need not be defined for point lengths.

The helper receives the caller-selected main dimension and resolved insets.
Returning false requires measurement even if an old basis exists; it leaves
generation unchanged so the future measurement branch can finish the operation.
This is not yet the complete child-basis visitor or a production solver change.

Proof: **720** fixtures call pinned `computeFlexBasisForChild` directly with row
and column parents, point/percentage/auto/intrinsic basis values, definite and
indefinite owner/available sizes, inset floors, and absent/existing cache values.
For these fixtures, native callback invocation identifies the required fallback.
Ard matches selection versus fallback, and the direct branches' Float32 basis
and generation. Fallback measured sizes and final generations are explicitly
excluded, not asserted to match the still-untranslated branch.

Two deterministic tests independently verify the cache/invalidation sequence
**10 → 10 → 20 → 9**, basis precedence and zero-space behavior.
`ard test test/layout_basis_test.ard`: **2 passed**; full `ard test`:
**391 passed, 0 failed, 0 panicked**. Compiler/formatter checks pass for all
three new/changed Ard files. All earlier differential cases pass.

Next is child measurement constraint construction (cross-axis stretch, scrolling,
maximum constraints), invoking the translated visit and storing its measured
main-axis basis. Container recursion and ADR-specific intrinsic policy remain.

## Leaf child-basis measurement fallback stage

`basis::measurement_axis` translates the fallback's constraint construction:
definite dimensions include margins; otherwise finite parent space supplies a
FitContent limit except along a scrolling main axis. Exact cross-axis stretch
then applies, followed by maximum constraints. Cooper exposes no aspect-ratio
style, so those upstream branches are not included. Inputs are processed lengths,
resolved bounds/insets and resolved alignment, not arbitrary raw Style values.

`Node.measure_leaf_basis` connects those constraints to the translated cached
leaf visit, stores the measured main-axis basis with its inset floor, and updates
basis generation. It does not commit layout dimensions or clear dirty state.
It remains a leaf-only path, outside the active application solver.

Proof: **32** native/Ard visits (16 fixtures, each repeated in the same generation)
match callback counts, callback content sizes and modes, measured width/height,
basis and generation. Fixtures combine row/column, scroll/non-scroll,
stretch/start, and max-bounded/unbounded with asymmetric margins and padding.
Unlike the earlier direct-basis matrix, this explicitly compares fallback results.
The deterministic integration test independently checks unbounded scroll width,
exact cross content height13, measured border box35×17, basis35, and one callback
over two visits. It also verifies a definite percentage cross dimension overrides
stretch. The test initially caught resetting the working axis before preserving
parent availability; the fixed implementation snapshots the parent constraint.

`ard test test/layout_basis_test.ard`: **3 passed**; full `ard test`:
**392 passed, 0 failed, 0 panicked**. Compiler and formatter checks pass for all
four changed Ard files. All previous differential checks pass.

Next is the general container visitor and flex-line collection, allowing child
basis measurement to recurse into containers. Public intrinsic/cycle adaptations
and final production integration still remain; Tess has not been removed.

## Flex-line and two-pass kernel; accepted wrapped auto-margin adaptation

`core/layout/flex.ard` now translates resolved-item line collection and the
main-size arithmetic of Yoga's first/second distribution passes. It owns no
tree traversal, callbacks or physical positioning yet. Four focused tests cover
line breaks/gaps, factor sums, asymmetric maximum-constrained grow (25,55),
minimum-constrained shrink (35,5), and raw contradictory-bound behavior.
Parent review restored source ordering for auto-margin counting and Float32
delta arithmetic. The differential runner now compares 32 line collection and
two-pass distribution cases against native Yoga; all match. Container integration
remains separate; kernel agreement alone does not prove whole-tree parity.

**Accepted: auto margins are counted per line.**
Pinned `FlexLine.cpp` increments `numberOfAutoMargins` before checking whether
the candidate fits the line. The rejected first item of the next line therefore
contributes its auto margins to the previous line's free-space division.
Cooper deliberately counts them only after accepting the item onto the line.

Reproduction: row width10, wrap enabled, align-content start, two children each
width6/height1/shrink0 with left auto margin. The first child fills line1 and
the second wraps to line2. Each line has four spare cells.

| Implementation | First child | Second child |
| --- | --- | --- |
| Pinned native Yoga | x2, y0, width6 | x4, y1, width6 |
| Current Cooper | x4, y0, width6 | x4, y1, width6 |

The native first line divides four spare cells by two margins, despite only one
item belonging to it. The user approved counting only margins belonging to
accepted items on each line, preserving current Cooper behavior. This is an
explicit additional adaptation to the pinned Yoga source, not an accidental
translation difference. The kernel test checks both sides of the line break.

Reproducible diagnostic fixtures (not public conformance expectations):
`test/layout_auto_margin_reference.cpp` and
`test/layout_auto_margin_reference.ard`. Run:

```sh
tess=$(go list -m -f '{{.Dir}}' github.com/AnatoleLucet/tess)
c++ -std=c++20 -I "$tess/etc/include" test/layout_auto_margin_reference.cpp \
  "$tess/etc/lib/linux_amd64/libyogacore.a" -o /tmp/cooper-auto-margin
/tmp/cooper-auto-margin
ard run test/layout_auto_margin_reference.ard
```

The observed output is the table above. The collection test rejects Yoga's
extra next-line margin and checks that the next line counts its own margin once.

## Child preparation and recursive visitor work in progress

`children.ard` prepares flattened layout children, skips absolute items, resets
hidden subtrees, resolves spacing, and applies the single-flex-child basis
optimization. Three tests cover traversal, asymmetric percentage references,
processed dimensions, and basis visitation.

`visitor.ard` is a dimension-only recursive container implementation under
review, not a production replacement or a claim of complete Yoga equivalence.
Seven focused tests cover nested rows/columns, wrapping, bounded grow/shrink,
cache invalidation, measurement versus committed dimensions, nonwrapping versus
wrapped FitContent overflow, and percentage cross gaps. The last two initially
failed (5 passed, 2 failed); translating the corresponding source paths gives
7 passed, 0 failed. Cache invalidation starts from a clean tree and checks that
changed content updates both leaf and parent widths from3 to7.

Before production integration, finish and differentially verify the container
source phases: cross-axis stretch and align-content, fixed-size measurement
shortcuts, scroll-specific sizing, and owner-relative constraint references.
Then translate positioning/absolute layout and connect pixel projection and
the accepted Cooper intrinsic/cycle adaptations. Neither these focused tests
nor the existing numeric differential matrix establish recursive visitor parity.
Runtime still uses the previous solver; Tess remains a dependency.

### Initial cross-axis stretch guards

The second-pass child constraint construction now follows Yoga's exclusions
for wrapping overflow and auto cross-axis margins. An eighth visitor test
failed before this correction and passes afterward. Native Yoga independently
confirms these heights in a10×12 row with6×2 measured children:

| Scenario | Child height |
| --- | --- |
| Two children wrap, align-content start | 2 each |
| One child, top auto margin and bottom1 | 2 |
| One child, no auto margins, no wrap | 12 |

Reproduce the native assertions with:

```sh
tess=$(go list -m -f '{{.Dir}}' github.com/AnatoleLucet/tess)
c++ -std=c++20 -I "$tess/etc/include" test/layout_cross_reference.cpp \
  "$tess/etc/lib/linux_amd64/libyogacore.a" -o /tmp/cooper-cross-reference
/tmp/cooper-cross-reference
ard test test/layout_visitor_test.ard --filter cross_stretch
```

These cases verify the initial stretch decision only; they do not establish
full cross-axis parity.

### Per-line stretch visitation

The visitor now measures stretch children during distribution and defers their
layout until the complete line cross extent is known. Nonwrapping line extents
honor the container's exact cross size and min/max bounds. The deferred visit
uses the child's measured main size and constrains both axes before applying
Yoga's wrap/align-content sizing modes.

The new `line_stretch` regression failed before implementation. A3×2 measured
child beside a4×5 fixed sibling now stretches to height5, or height8 with a
container minimum of8, while keeping width3. The native reference above asserts
the same dimensions for both child and container. All nine visitor tests pass.

Align-content remeasurement across multiple lines, fixed-size measurement
shortcuts, and full owner-relative constraint parity remain unfinished. This
code still does not position children or replace the production solver.

### Multi-line remeasurement and the ADR0017 integration adaptation

The visitor now retains line membership and runs the dimension portion of
Yoga step8 for wrapped containers. The initial positive-space stretch regression
failed before implementation; the expanded matrix passes all21 combinations
of seven align-content modes and positive/zero/negative cross free space.
`test/layout_cross_reference.cpp` independently asserts the same native results.
The ten visitor tests pass. Positions and baseline line extents remain separate
unfinished work, as do fixed-size shortcuts and owner-relative constraints.

The matrix uses a10-wide row, two wrapped children of natural heights2 and4,
gap2, and container heights14/8/4. The first child has auto height; the second
has explicit height4. At height14, the first child's resulting heights are:

| Mode | Native Yoga and raw visitor | ADR0017 public requirement |
| --- | --- | --- |
| start/end/center | 2 | 2 |
| stretch | 5 | 5 |
| space_between | 8 | 2 |
| space_around | 5 | 2 |
| space_evenly | 4 | 2 |

At heights8 and4 all modes leave the first child at2. The explicit sibling
stays4 throughout. Pinned Yoga includes `leadPerLine` in the exact cross size
sent to the child during step8. Preserve this in the raw translation, but
**exclude distributed spacing from child sizing at the Cooper integration
boundary**, as already required by accepted ADR0017. No new contract approval
is needed. These native expectations must not become public conformance tests.
The same source also adds the cross-axis margin to a column child's main size;
that path is preserved but not covered by this row-only matrix.

### Fixed-size container measurement shortcut

The visitor now skips container traversal when both margin-adjusted axes meet
Yoga's fixed-size predicate and the request is measurement-only. Exact axes
qualify; FitContent qualifies only at a defined nonpositive size. Bounds and
padding floors still apply. Contents-only descendant paths are cleaned without
visiting box descendants. A later full layout does not reuse this shortcut to
skip child layout.

The retained regression failed before implementation and now passes, checking
zero child callbacks, an untouched child basis, cleared nested contents geometry,
uncommitted parent geometry, and subsequent full layout. The numeric differential
runner adds225 comparisons against the actual private Yoga
`measureNodeWithFixedSize` function: five sizes (undefined, -1,0,0.01,8) on each
axis and all nine mode pairs, with asymmetric min/max and padding. All match.
Full `ard test`:410 passed,0 failed,0 panicked; compiler and formatter checks pass.

Remaining container work includes `canSkipFlex`, scroll-specific final sizing,
baseline line extents, and owner-relative constraint parity. Positioning,
accepted-policy integration, and removal of Tess remain pending.

## Production integration completed

The remaining phases above are integrated. `visitor::calculate` is the sole
retained layout entry; no independent solver or Tess fallback remains.

- `visitor` orders basis calculation, line collection, distribution, recursive
  measurement/layout, deferred stretch, multiline remeasurement and positioning.
  It includes fixed-size and exact-cross-axis measurement shortcuts and
  overflow-scroll final sizing.
- `position` implements justification, auto margins, cross alignment, reverse
  axes and baseline placement. Root relative offsets resolve against the
  viewport; static roots ignore them. Auto cross margins suppress alignment
  even when their available space is negative.
- `absolute` implements measure-then-layout and containing-block traversal,
  skipping static and contents ancestors where required. Border/padding-box
  references and asymmetric inset placement have dedicated tests.
- Production policy adapters implement intrinsic keywords and percentage
  provenance (0016), line spacing separate from child size (0017), bottom-box
  baselines (0018), contents flattening (0019), and transaction-local projected
  width replay with frozen horizontal geometry (0020). Iterative constraint
  redistribution is isolated in `redistribute`; raw two-pass Yoga tests remain.
- Natural measurements and basis caches survive projected-width replay.
  Integral measured widths skip replay; unchanged root transactions skip the
  visitor. Changed content still invalidates the owning chain.
- Tess and its checksums are removed from root/examples modules, and the unused
  `retainedyoga` bridge is deleted. Native comparison tools obtain Tess only in
  an isolated historical worktree. Production Go boundary tests and quickstart
  compilation succeed with `CGO_ENABLED=0`.

Final headless verification: `ard test` reports **430 passed, 0 failed,
0 panicked**. The pinned-source comparison passes 14 shared geometry cases,
one intentional intrinsic adaptation, 169 numeric pairs, 5,184 cache decisions,
12 rounding cases, five cached leaf visits, 2,016 axis cases, 60 lengths,
1,728 processed dimensions, 720 direct basis cases, 32 basis fallback visits,
32 two-pass flex distributions and 225 fixed-size shortcut cases.

These are bounded differential tests plus public contract/regression tests,
not the entire upstream Yoga suite. Unsupported Yoga configurations, RTL,
aspect-ratio APIs and arbitrary baseline callbacks are not added by this port.
Performance results and remaining profiling opportunities are recorded in
`layout-performance-comparison.md`; performance parity is not a completion
claim.
