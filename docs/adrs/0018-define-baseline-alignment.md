# 0018: Define Baseline Alignment

## Status

Accepted

## Context

Cooper publicly accepts baseline alignment but exposes no baseline callback or
reference-child selection API. A terminal cell has no font ascent/descent
metric. Yoga can synthesize baselines recursively from descendants, making
layout depend on an implicit child-selection rule.

OpenTUI advertises baseline alignment and forwards it to Yoga without a public
renderable baseline callback. Its raw wrapper exposes a reference-baseline flag.
That precedent does not establish a text-row baseline contract for Cooper.

## Decision

### Use a deterministic box baseline

Define a node's baseline as its bottom border-box edge, excluding bottom margin.
For a zero-height node it is its top edge. Apply this rule to text, controls,
custom renderables, and containers alike. Do not derive a container baseline
from a descendant, a caret, or the first/last displayed text row.

For example, put two boxes in a horizontal row: A is one cell tall and B is
three cells tall. Baseline alignment moves A down until both boxes end at the
same horizontal edge. Here, each printed row represents exactly one terminal
cell row; letters mark cells occupied by a box, and dots mark empty space.
The baseline is an edge **between** cell rows, not a row of cells itself.

```diagram
No margins: baseline alignment looks like bottom alignment.

cell row       A     B
   0           .     B
   1           .     B
   2           A     B
            ─────────────  baseline at edge y=3
```

The result is A at y=2 with height 1, and B at y=0 with height 3.
Both bottom edges are at y=3. Changing B's children without changing B's
own height does not change that edge.

For each row flex line, align participating items to the same baseline. Its
required cross extent includes the largest ascent (top margin plus border-box
height) and largest descent (bottom margin), with a non-negative final extent.
Non-baseline items still contribute their margin-box cross extents. Place the
baseline group from the physical top of the line, even with `wrap_reverse`;
reversing line placement does not invert text or the baseline metric.

Now give A a bottom margin of two cells; B still has no margin. The boxes still
end at y=3, but A reserves two empty rows below the baseline. The flex line must
therefore be five cells tall: three above the baseline and two below it.
The `m` symbols below mark A's reserved margin space; they are not painted cells.

Compare baseline alignment with end alignment in that same five-cell line:

```diagram
             baseline alignment              end alignment
cell row       A     B                         A     B
   0           .     B                         .     .
   1           .     B                         .     .
   2           A     B                         A     B
            ─────────────  baseline y=3
   3           m     .                         m     B
   4           m     .                         m     B
            ─────────────                   ─────────────
             line ends y=5                   line ends y=5
```

Baseline alignment lines up the **boxes' bottom edges**: A and B both end at
y=3. End alignment lines up the **margin boxes' bottom edges**: A's box plus its
margin ends at y=5, and B's box ends at y=5. This is why baseline cannot simply
be implemented as an alias for end alignment.

Baseline applies independently on each wrapped row line. In column and
column_reverse layouts it behaves as cross-axis start alignment; there is no
vertical text baseline. A contents node has no box and contributes no baseline;
its participating descendants use their own boxes (ADR 0019).

### Keep custom baselines out of this contract

Do not add a callback merely to emulate browser typography. A future proposal
may introduce explicit cell-row baselines if actual controls need them. Such a
proposal must define container propagation, invalidation, and text wrapping.

### Acceptance checks

Test unequal heights, unequal top/bottom margins, zero height, padded/bordered
text, multiline text, and a nested container whose first child changes height
without changing its own border box. Cover multiple lines, row_reverse,
wrap_reverse, both column directions, and retained resize/reparent mutations.
Assert line extents as well as item positions; equal-height examples cannot
distinguish baseline policies.

## Consequences

- Baselines are predictable from public geometry, without hidden child selection.
- This intentionally differs from recursive Yoga fallback and does not promise
  first-line text alignment. The Ard engine implements the metric directly;
  migration notes and executed evidence are in the layout audit.
- Baseline remains distinct from end alignment when margins differ.
- Implemented with box, margin, wrapped-line, retained-mutation, contents, and
  projected-text checks in `test/baseline_test.ard`.

## Related

- [ADR 0017: Item Alignment and Line Distribution](./0017-define-item-alignment-and-line-distribution.md)
- [ADR 0019: Display Contents](./0019-define-display-contents.md)
- [Layout conformance audit](../layout-conformance-audit.md)
- [OpenTUI alignment setup](https://github.com/anomalyco/opentui/blob/ac753b48d386707a931dcf881d0741905b64b4f9/packages/core/src/Renderable.ts#L742-L746)
- [OpenTUI raw reference-baseline API](https://github.com/anomalyco/opentui/blob/ac753b48d386707a931dcf881d0741905b64b4f9/packages/core/src/yoga.ts#L938-L998)
