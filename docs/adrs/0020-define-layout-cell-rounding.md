# 0020: Define Layout Cell Rounding

## Status

Accepted

## Context

Public geometry uses integer terminal cells, but percentages, flex allocation,
centering, and distribution create fractional positions. Rounding each width
independently loses or creates cells. Backend text-specific rounding can also
give measured leaves different geometry from otherwise identical containers.

OpenTUI documents whole-cell edge rounding and the example 31 cells split into
10/11/10. Its native Yoga configuration uses point scale 1. Its renderable path
does not expose text-node classification for Yoga's special text rounding.
Cooper needs an explicit rule rather than depend on backend classification.

## Decision

### Round absolute edges once

Retain fractional values through sizing, flex allocation, constraints, line
placement, and ancestor offset accumulation. At final cell projection, round
each absolute edge to its nearest integer, with exact half ties toward positive
infinity: `R(x) = floor(x + 0.5)`. Apply the same rule to negative coordinates.

Compute width as rounded right minus rounded left, and height as rounded bottom
minus rounded top. Derive local coordinates by subtracting rounded parent
origins, not by independently rounding local offsets. Never use projected cells
as fresh fractional layout inputs on the next render.

```diagram
31 cells, equal shares
ideal edges       0          10⅓          20⅔          31
rounded edges     0           10           21          31
                  ├───────────┼────────────┼───────────┤
widths                 10            11          10

Nested origins: parent 0.4 + child 0.4 = absolute 0.8
Round absolute: child screen x=1; parent screen x=0; child local x=1
Round separately: 0 + 0 = 0  ✗
```

Equal ideal edges must project to equal cell edges, so contiguous items remain
contiguous and exactly tiled spans preserve their rounded total. This is not a
promise that children fill a parent when layout deliberately leaves gaps or
overflows. Rounding may collapse a sub-cell span or gap to zero. Do not force a
one-cell minimum; that would violate zero-size support and shared-edge geometry.

```diagram
tie policy       -1.5  -0.5   0.5   1.5
rounded            -1     0     1     2

5 cells, two equal shares: ideal edges 0, 2.5, 5
rounded edges 0, 3, 5 → widths 3, 2
Reverse placement changes item identity at each edge, not the rounding rule.
```

### Use one cell model for measured and unmeasured nodes

Apply the same edge rule to Text, controls, and containers. Do not ceil text
widths or floor text origins as a separate projection rule. Measurement uses
display-cell widths, not bytes or code points; a wide glyph still occupies two
cells under Cooper's existing painting rules.

Width-dependent text/control measurement must use the eventual allocated cell
width before committing dependent height and caret geometry. If fractional
allocation predicted a different wrapping width, remeasure at the projected
width and resolve dependent layout before publishing the frame. This does not
grant the leaf extra width or permit it to overwrite its sibling. An
implementation must converge without emitting an intermediate inconsistent
frame; designing that measurement/layout reconciliation is implementation work.

### Freeze horizontal allocation during reconciliation

Select flex-line membership, fractional horizontal sizes, insets, and physical
horizontal positions in the contribution layout. Finish horizontal relative and
absolute positioning, then derive measured leaves' projected content widths
from those absolute edges. Freeze these decisions for the rest of this layout
transaction.

Remeasure at the allocated cell widths and resolve dependent heights, vertical
flex allocation, and vertical positions within the selected lines. Do not reform
lines or revise horizontal allocations in response to the corrected heights.
Spare space or overflow may remain in a selected line. Each new layout starts
afresh from styles, content, and available space; previous projected geometry is
never the next transaction's fractional input. Natural-width probes do not use
allocated-width measurements.

This rule is necessary because repacking can have no fixed point. In a 5×2
column/wrap_reverse container, put a one-row Box followed by character-wrapped
Text `abc`, both width 50% with grow/shrink zero. If Text is one row, both items
fit in one column: its edges 2.5/5 project to width 2, requiring two text rows.
If Text is two rows, it moves to a second column: edges 0/2.5 project to width 3,
requiring only one row. Repacking would alternate forever. Under this rule the
contribution pass selects two columns; they remain selected when the Text's
corrected height becomes one row.

```diagram
Text "abc", wrapping enabled, allocated cell width 2
┌──┐
│ab│  measured height = 2
│c │  not height 1 from an earlier unconstrained measurement
└──┘
```

Apply retained integer scroll/translation offsets once to projected geometry.
Paint, hit testing, clipping, caret placement, reveal, and selection all consume
the same committed cell rectangles. A translation must not trigger a second
rounding pass or change widths.

### Acceptance checks

Test 31/3 and 5/2 splits, negative half ties, nested fractional origins, zero and
sub-cell spans, percentage edges, gaps, reverse directions, and nonzero scroll
offsets. Assert exact edges and totals with independently calculated values.
Pair measured and unmeasured nodes with the same ideal rectangles; test wrapping
at a projected-width boundary, wide cells, and caret/hit agreement. Compare
resize cycles and retained mutations with fresh layouts to catch rounding drift.

## Consequences

- Fractional allocation has deterministic, backend-independent cell output.
- Ties are intentionally asymmetric about zero; reversing item order can change
  which identity receives an extra cell.
- Uniform geometry may differ from Yoga's measured-text rounding. Measurement
  and projection cannot be implemented as unrelated final steps.
- This decision defines observable output, not a required numeric representation
  or a claim that the current backend already conforms.
- Acceptance establishes the contract; runtime implementation and conformance
  tests remain pending.

## Related

- [ADR 0016: Intrinsic Sizing and Constraints](./0016-define-intrinsic-sizing-and-constraints.md)
- [ADR 0017: Item Alignment and Line Distribution](./0017-define-item-alignment-and-line-distribution.md)
- [ADR 0005: Rich Text and Wrapping](./0005-define-rich-text-wrapping-and-multi-click-selection.md)
- [Layout conformance audit](../layout-conformance-audit.md)
- [OpenTUI rounding documentation](https://github.com/anomalyco/opentui/blob/ac753b48d386707a931dcf881d0741905b64b4f9/packages/web/src/content/docs/core-concepts/layout.mdx#L160-L190)
- [OpenTUI point-scale configuration](https://github.com/anomalyco/opentui/blob/ac753b48d386707a931dcf881d0741905b64b4f9/packages/native/src/yoga.zig#L174-L185)
