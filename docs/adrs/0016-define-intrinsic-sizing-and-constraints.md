# 0016: Define Intrinsic Sizing and Constraint Resolution

## Status

Accepted

## Context

Cooper publicly accepts `max_content`, `fit_content`, and `stretch` for
dimensions, flex basis, and minimum/maximum constraints. Their names imply
distinct sizing policies, but accepting and forwarding these values does not
prove that the backend implements those policies.

A measured Text containing `abc defgh`, configured with width `max_content`
and shrink zero beneath a column parent with `align_items: start`, available
width 5 and visible overflow, currently receives a 5×2 layout. Its unwrapped
intrinsic size is 9×1. The pinned backend's child measurement path applies a
finite available-width constraint rather than honoring the intrinsic keyword.
The runtime probe established the resulting geometry; the constraint path was
identified through source inspection, not a logged measurement callback.

The boxes below show Text bounds, not parent clipping. The parent is five cells
wide in both cases; the accepted `max_content` contract allows a wider child.

```diagram
Current: constrained measurement     Contract: intrinsic measurement
┌─────┐                             ┌─────────┐
│abc  │  Text: 5×2                  │abc defgh│  Text: 9×1
│defgh│                             └─────────┘
└─────┘                              ◀──5──▶    parent width
```

Cooper needs independently testable sizing rules whether it retains Tess or
implements layout in Ard. Tinear is an integration reference, not the definition
of the supported vocabulary. This decision separates preferred sizing, flex
allocation, bounds, text remeasurement and clipping so one stage cannot silently
stand in for another.

### OpenTUI is a reference, not an intrinsic-keyword specification

Inspected OpenTUI at
[this revision](https://github.com/anomalyco/opentui/commit/ac753b48d386707a931dcf881d0741905b64b4f9).
Its [ordinary renderable API](https://github.com/anomalyco/opentui/blob/ac753b48d386707a931dcf881d0741905b64b4f9/packages/core/src/Renderable.ts#L61-L100)
and [layout documentation](https://github.com/anomalyco/opentui/blob/ac753b48d386707a931dcf881d0741905b64b4f9/packages/web/src/content/docs/core-concepts/layout.mdx)
have a narrower vocabulary than Cooper:

| Concern | OpenTUI behavior | Implication for this decision |
| --- | --- | --- |
| Dimensions | Numbers, percentages and `auto`; no public max-content/fit-content size keywords. | Cooper's intrinsic keywords are an extension, not OpenTUI parity. |
| Stretch | An alignment mode, not a dimension keyword. | Sizing `stretch` needs its own justification and tests. |
| Flex basis | Numbers or `auto` in ordinary renderables; percentage basis is available in the advanced Yoga facade. | Cooper exposes a broader ordinary basis contract. |
| Automatic content size | Yoga derives it from children or a measure function. Word/character wrapping responds to finite width. | Preserve the distinction between unconstrained, at-most and exact measurement. |
| Min/max | Forwarded to Yoga; `auto` is ignored despite appearing in some public types. | Cooper should retain explicit validation, not copy a type/runtime mismatch. |
| Default shrink | Initially zero if either width or height is numeric, otherwise one, unless overridden. | Keep Cooper's stable default of one and its explicit scroll-child policy; do not copy this axis-insensitive heuristic. |
| Indefinite percentages | Docs warn that an indefinite parent can differ from browser behavior; no independent OpenTUI rule. | The cycle rules below are Cooper policy, not an upstream guarantee. |
| Rounding | Scale-one Yoga edge rounding; equal flex siblings may receive unequal integer widths while preserving their shared span. | Use rounded edges rather than independently rounded widths; exact Cooper tie rules still need tests. |

OpenTUI vendors Yoga 3.2.1 through its
[dependency update script](https://github.com/anomalyco/opentui/blob/ac753b48d386707a931dcf881d0741905b64b4f9/packages/native/src/vendor/update-zig-deps.sh#L8-L15).
Its [production config](https://github.com/anomalyco/opentui/blob/ac753b48d386707a931dcf881d0741905b64b4f9/packages/native/src/yoga.zig#L174-L185)
disables web defaults and sets point scale to one; its renderables then apply
their own defaults. Cooper's Tess configuration and explicit styles differ.
Neither "Yoga behavior" nor "OpenTUI defaults" is a sufficient Cooper contract.

The [Yoga callback contract](https://github.com/anomalyco/opentui/blob/ac753b48d386707a931dcf881d0741905b64b4f9/packages/core/src/tests/yoga-upstream/tools/utils.ts#L22-L45)
distinguishes intrinsic measurement from a finite constraint:

```diagram
┌─────────────────────────┐     ┌─────────────────────────────────┐
│ Undefined               │────▶│ Measure natural content extent  │
│ AtMost(available)       │────▶│ Fit within available extent     │
│ Exactly(allocated)      │────▶│ Use the allocated extent        │
└─────────────────────────┘     └─────────────────────────────────┘
```

OpenTUI does not establish the required 9×1 result through a max-content style:
it has no such public style. Keeping Cooper's existing keywords therefore means
owning additional semantics and implementation work. Deliberately narrowing the
API to OpenTUI's vocabulary is an alternative to this decision, not something to
do silently while fixing the backend.

## Decision

### Units and available space

Cooper uses a horizontal writing model. Width is horizontal terminal space;
height is vertical terminal space. Row/column flex direction does not swap the
meaning of width, height, padding or physical edges.

Configured sizes and min/max constraints describe the border box. Intrinsic
content measurements exclude the node's own padding and border; sizing adds
those insets once. Margins remain outside the border box. Content dimensions
cannot be negative. If the requested border box is smaller than its padding and
border, the insets establish its minimum physical extent; clipping is separate.

```diagram
          margin: outside the configured size
     ┌─────────────────────────────────────┐
     │ border box: configured width/height │
     │  ┌───────────────────────────────┐  │
     │  │ padding                       │  │
     │  │  ┌─────────────────────────┐  │  │
     │  │  │ measured content        │  │  │
     │  │  └─────────────────────────┘  │  │
     │  └───────────────────────────────┘  │
     └─────────────────────────────────────┘

Content 3×1 + padding 1 per side + border 1 per side = border box 7×5
```

A definite available dimension is known without deriving it from the content
currently being measured. It may be zero. An indefinite dimension has no finite
limit for that measurement pass. Implementations must represent these states
distinctly; zero is never a spelling of undefined or infinity.

Available space for a child's preferred border-box size excludes the containing
box's border/padding and the child's resolved margins. Auto margins count as
zero during sizing and receive free space during alignment. Flex allocation
accounts for sibling sizes and gaps separately; `stretch` does not mean
"whatever is left after placing previous siblings."

### Preferred dimension policies

| Length | Preferred sizing rule |
| --- | --- |
| `cells(n)` | Request a border-box dimension of n. |
| `percent(p)` | Request p percent of the corresponding definite containing content dimension. |
| `undefined` / `auto` | Use the existing automatic flex sizing policy; neither forces intrinsic size nor disables alignment stretch. Undefined also clears a previously supplied value. |
| `max_content` | Request the natural content extent without a finite available limit on the queried axis, plus the node's insets. |
| `fit_content` | Request the smaller of the natural extent and definite available space; with indefinite space, use the natural extent. Remeasure dependent dimensions under the chosen size. |
| `stretch` | Request the definite available extent even when content is smaller; with indefinite space, use the natural extent. |

These are preferred sizes, not guarantees of the final size. Applicable min/max
constraints and main-axis flex allocation can change them. An explicit intrinsic
cross-axis width is not converted to automatic stretch merely because the
parent defaults to `align_items: stretch`.

Cooper's `fit_content` is deliberately a bounded terminal-sizing policy, not a
promise of CSS's min-content floor. A long word can be grapheme-wrapped according
to the control's wrap mode. A wide grapheme that cannot fit is never split into
partial painted cells; existing clipping and source-mapping rules still apply.
This decision adds no `min_content` value or CSS conformance claim.

For the same `abc defgh` content, the required border-box sizes are:

```diagram
Available width 5                  Available width 12

max_content                        max_content / fit_content
┌─────────┐                        ┌─────────┐
│abc defgh│  9×1                   │abc defgh│  9×1
└─────────┘                        └─────────┘

fit_content / stretch              stretch
┌─────┐                            ┌────────────┐
│abc  │  5×2                       │abc defgh   │  12×1
│defgh│                            └────────────┘
└─────┘
```

### Natural size belongs to controls and containers

For Text, natural width is the widest explicit source line measured with the
Runtime's terminal-width measurer. Soft wrapping, ellipsis and ancestor clipping
do not reduce this intrinsic width. Explicit newlines, tabs, Unicode graphemes
and hidden text retain their existing source/measurement semantics.

Natural height is evaluated after the applicable width has been resolved. It
includes all resulting rows, including explicit empty/trailing lines, without a
height cap. Therefore `height: max_content` does not disable wrapping at an
explicit finite width. Width is resolved before width-dependent height; the
solver must not iterate between alternate widths merely to fit a height cap.

```diagram
┌────────────────────┐     ┌────────────────────┐     ┌───────────────┐
│ Natural width: 9   │────▶│ max_width: 5       │────▶│ Remeasure     │
│ "abc defgh"        │     │ Final width: 5     │     │ Height: 2     │
└────────────────────┘     └────────────────────┘     └───────────────┘

Clipping a 9×1 box to five visible columns is different:
it shows only "abc d" and does not produce a second row.
```

Input and TextArea retain their own measurement contracts, including caret room,
placeholder measurement, wrapping, and private scrollbar gutters. This decision
does not replace those controls with Text-style measurement.

Containers derive natural extents from their in-flow layout participants, not
from the characters ultimately visible in a frame. On an unbounded main axis,
children use their hypothetical sizes without distributing fictitious infinite
free space or introducing soft flex-line breaks. Along a bounded main axis,
normal line formation and flex sizing apply before deriving a natural cross
extent. Include resolved child margins, gaps, padding and border. Exclude
absolute-positioned and display-none children from the container's natural
in-flow extent. Reverse direction changes placement, not the amount of natural
space required. Descendant explicit sizes and constraints still apply.

For example, with no flex factors, margins or insets, two fixed children of 3×1
and 5×2 with a one-cell gap have natural size 9×2 in a row and 5×4 in a column.
Determining which descendants participate for `display: contents` remains a
separate retained-tree contract, specified in ADR 0019.

### Percentages must not make intrinsic measurement circular

Width percentages use containing content width; height percentages use containing
content height. An unresolved percentage preferred size behaves as auto for that
measurement pass. An unresolved percentage min/max constraint contributes no
bound in that pass. Percentage flex basis with an indefinite main-axis reference
uses content sizing rather than manufacturing a zero-sized basis.

An ancestor size determined independently by explicit sizing, stretch or final
flex allocation can subsequently provide a definite percentage reference. In
that case, remeasure affected descendants before committing geometry. A size
obtained solely by measuring those same descendants must not be fed back as a
new percentage reference on that axis. This avoids circular expansion and makes
repeated unchanged layout deterministic.

```diagram
Definite reference                 Circular reference
┌───────────────────────┐          ┌───────────────────────┐
│ Parent content: 40×20 │          │ Parent: content-sized │◀──┐
└───────────┬───────────┘          └───────────┬───────────┘   │
            ▼                                  ▼               │
┌───────────────────────┐          ┌───────────────────────┐   │
│ Child: 25% × 50%      │          │ Child: percentage     │───┘
│ Resolves to 10×10     │          │ Needs parent size     │
└───────────────────────┘          └───────────────────────┘

Cycle break: unresolved preferred percentage uses auto for this pass.
Remeasure only if an independently definite reference becomes available.
```

For completeness, percentage padding, margins and gap need reference rules too:
all physical padding/margin percentages use containing content width; gap uses
the container content dimension on the axis where that gap is applied. A cyclic
percentage spacing contribution is zero during intrinsic contribution sizing.
If its reference becomes independently definite, resolve it for final layout;
do not expand an intrinsically sized ancestor repeatedly to absorb it. This
decision deliberately makes that behavior explicit rather than inheriting a
backend-specific fixed-point calculation.

### Bounds and flex allocation are distinct from measurement

Resolve a node's intrinsic constraint keywords using the same natural/available
quantities as preferred dimensions, without applying the node's own min/max
constraints recursively while obtaining those quantities. Descendant constraints
still participate. Undefined min/max means no explicit bound; auto remains
invalid for min/max. `min_width: max_content` is consequently an explicit request
not to shrink below natural width, not an alias for `width: max_content`.

After resolving bounds, clamp a proposed size by maximum and then minimum:
minimum wins when both conflict. Physical insets remain a floor. Bound resolution
does not change the meaning of zero or silently turn an indefinite bound into a
finite one.

An explicit flex basis controls the main-axis base independently of a conflicting
preferred main-axis dimension. Intrinsic basis keywords use their content sizing
policy on the main axis. Auto/undefined basis consults the preferred main-axis
dimension and otherwise uses automatic content sizing. Neither `max_content`
nor `fit_content` implicitly sets grow or shrink to zero.

Flex grow/shrink distributes free space from the bases, respecting the existing
factor rules. Shrink weights include the base size. Freeze items that reach
their min/max bounds and redistribute remaining space among eligible siblings;
do not merely clamp the result of one distribution. If all items are frozen,
unresolved overflow remains overflow. Cooper's existing no-shrink policy for
immediate children of scrolling nodes remains in force.

```diagram
Row available width: 90; bases: A=80, B=40; equal shrink factors

Weighted shrink             Freeze A at min_width 70      Redistribute
┌────────────┬──────┐        ┌──────────────┬──────┐        ┌──────────────┬────┐
│ A: 60      │ B:30 │───────▶│ A: 70        │ B:30 │───────▶│ A: 70        │B:20│
└────────────┴──────┘        └──────────────┴──────┘        └──────────────┴────┘
Total 90                    Total 100: not final           Total 90
```

Once allocation determines final width, remeasure width-dependent height and
settle cross-axis sizing before publishing geometry. A changed width may wrap
Text even when its original preferred width was max-content. No clipping policy
is allowed to masquerade as a size constraint.

### Conformance examples

Unless stated otherwise, examples have no padding, border, margin or gap,
use column flow with start cross alignment, and disable flex shrink. Text uses
the normal one-cell ASCII measurer and default word wrapping. These are required
expected results, not claims about the current implementation.

| Case | Expected border-box result |
| --- | --- |
| `abc defgh`, max-content width, parent width 5 | 9×1; extends beyond the parent. |
| Same, fit-content width, parent width 5 | 5×2. |
| Same, fit-content width, parent width 20 | 9×1, not 20×1. |
| Same, stretch width, parent width 20 | 20×1. |
| Same, max-content width and max-width 5 | 5×2 after constraint and remeasurement. |
| Same, width 5 and max-content height | 5×2; intrinsic height does not undo the finite width. |
| `abc` followed by an explicit newline and `defgh`, max-content width | 5×2. |
| `abc`, max-content width, one-cell padding on all sides and one-cell border | 7×5; content 3×1 plus four cells of insets on each axis. |
| Requested width 8, min-width 7, max-width 4 | Width 7; minimum wins. |
| Parent content 40×20; child width 25%, height 50% | 10×10; dimensions use different reference axes. |
| Row width 90, bases 80/40, equal shrink | Widths 60/30. With first minimum 70: 70/20. |

Test finite space below/equal/above intrinsic size, and zero separately from
indefinite. Test measured leaves and nested containers, both flex directions,
constraint replacement, percentage references becoming definite after allocation,
and dirty text/wrap changes. Assert sibling geometry as well as the measured
node's rectangle. Compare retained mutation with fresh-tree layout, but derive
numeric expectations independently of either implementation.

Fractional arithmetic must be retained until final cell projection; per-child
early integer truncation is not acceptable. Exact tie-breaking, shared-edge
rounding and measured-text edge rules are specified separately in ADR 0020.
The integral examples here intentionally avoid depending on those rounding
choices. Alignment distribution and baseline behavior are specified in ADRs
0017 and 0018 rather than this decision.

OpenTUI's documented edge-rounding example illustrates why this distinction
matters. Three equal shares of 31 cells have ideal edges at 0, 10⅓, 20⅔ and 31:

```diagram
Rounded edges:       0          10           21          31
                     ├──────────┼───────────┼──────────┤
Widths from edges:        10           11          10       total 31

Round each width:         10           10          10       total 30 ✗
```

### Implementation and conformance

Implement and test these rules through Cooper's current validated API before
calling the keywords supported under this contract. Existing successful tests
remain required. In particular, add the 9×1 max-content regression without
changing its expected value to the current 5×2 backend fallback.

A fix must cover container sizing, constraints, basis, invalidation and dependent
measurement, not special-case one string or convert max-content to a one-time
fixed width. A narrowly scoped Ard sizing adapter is an implementation option;
an upstream backend correction is another. This ADR does not choose between them
without testing their complete effect on the contract.

Keep known backend limitations explicit until fixed. Do not silently replace
unsupported keywords with auto, remove public values as part of the adapter, or
claim that accepting a Style constructor validates executable behavior.

## Consequences

- Applications can choose intrinsic, bounded and filling sizes intentionally.
- Intrinsic size, allocation, constraints and clipping have independently
  testable responsibilities. Max-content does not promise immunity from flexing.
- Fit-content and cyclic percentage policies are explicit Cooper choices, not
  accidental claims of complete CSS or Yoga compatibility.
- OpenTUI demonstrates automatic intrinsic measurement and cell-edge rounding,
  but does not supply public semantics for Cooper's intrinsic size keywords.
  Retaining these keywords intentionally exceeds OpenTUI's ordinary API.
- Correct implementation may require backend changes or an Ard sizing layer;
  the existing measurement callback alone does not decide parent constraints.
- This decision does not settle baseline/item-alignment vocabulary,
  display-contents retained semantics, or exact fractional rounding. Those
  decisions have accepted contracts in ADRs 0017–0020, linked below; they must
  not be smuggled into intrinsic sizing fixes.
- Acceptance establishes the contract; runtime implementation and conformance
  tests remain pending.

## Related

- [ADR 0017: Item Alignment and Wrapped-Line Distribution](./0017-define-item-alignment-and-line-distribution.md)
- [ADR 0018: Baseline Alignment](./0018-define-baseline-alignment.md)
- [ADR 0019: Display Contents](./0019-define-display-contents.md)
- [ADR 0020: Layout Cell Rounding](./0020-define-layout-cell-rounding.md)
- [ADR 0002: Define the Application API](./0002-define-application-api.md)
- [ADR 0005: Define Rich Text, Wrapping, and Multi-Click Selection](./0005-define-rich-text-wrapping-and-multi-click-selection.md)
- [ADR 0007: Define Scrollbars and Two-Axis Scrolling](./0007-define-scrollbars-and-two-axis-scrolling.md)
- [ADR 0011: Define the Multiline TextArea](./0011-define-multiline-text-area.md)
- [Public layout conformance audit](../layout-conformance-audit.md)
- [Ard layout evaluation](../ard-layout-evaluation.md)
- [Pinned Yoga sizing modes](https://github.com/AnatoleLucet/tess/blob/c76872ba846380681de892662caaca9bdfa0d3bc/etc/include/yoga/algorithm/SizingMode.h)
- [Pinned Yoga layout algorithm](https://github.com/AnatoleLucet/tess/blob/c76872ba846380681de892662caaca9bdfa0d3bc/etc/include/yoga/algorithm/CalculateLayout.cpp)
