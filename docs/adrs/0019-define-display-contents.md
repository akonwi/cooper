# 0019: Define Display Contents for Retained Nodes

## Status

Accepted

## Context

`Display::contents` is already public in Cooper. Flattening only the layout
backend is insufficient: retained nodes also own geometry, painting, clipping,
scrolling, hit testing, focus, and event ancestry. Current paint traversal does
not give contents nodes a distinct boxless path.

OpenTUI's raw Yoga enum and parser include contents, but ordinary renderable
layout options do not expose display. It supplies no public retained-contents
contract to copy. Cooper must either define its existing feature or deliberately
remove it; this decision retains it as a structural grouping node.

## Decision

### Flatten boxes, preserve ownership

A contents node has identity and children but no layout or painted box. Splice
its participating descendants into the nearest box-generating ancestor's child
sequence in retained tree order, recursively through nested contents nodes.
`none` still suppresses its whole subtree. A contents leaf contributes nothing.

```diagram
Retained tree                    Effective layout / stacking children
┌─────────────┐                  ┌─────────────┐
│ row parent  │                  │ row parent  │
└──────┬──────┘                  └──────┬──────┘
       ├── A                            ├── A
       ├── group (contents)             ├── B
       │   ├── B                        ├── C
       │   └── C                        └── D
       └── D

The parent's gap appears between A/B, B/C, and C/D.
B's events still bubble through group before parent.
```

The contents node's dimensions, margins, padding, borders, flex factors,
alignment, positioning, overflow, and z_index have no box effect. It establishes
neither a containing block nor a scroll/clip boundary. Absolute descendants find
their containing block through box-generating ancestors. Validate stored Style
values normally even while they have no box effect.

Foreground/background inheritance still passes through it, but it performs no
background fill, border drawing, owner paint callback, or cursor placement.
It is not a stacking context: sort the flattened children by their own z_index
with stable effective tree order for ties, as for direct children.

### Make geometry an empty coordinate anchor

Expose zero width and height for a contents node, not a union of descendants.
Its local origin is (0,0); its screen origin is the retained parent's child
coordinate origin, including existing ancestor scroll translation. Its children
receive local geometry in that same coordinate system. A contents chain adds no
offset. This preserves coordinate accumulation without inventing a box.

```diagram
parent child-coordinate origin on screen: (4,2)
group contents: local (0,0,0,0), screen (4,2,0,0)
B:              local (3,1,2,1), screen (7,3,2,1)

group has no hit rectangle; B does.
Ancestor scrolling translates both anchors and B exactly once.
```

Contents nodes cannot be direct pointer targets or focus targets and contribute
no selection cells. Descendant hit testing, focus, selection, reveal, and clipping
continue through the grouping node. Attempting to focus the group fails using
the existing conditional focus outcome; switching a focused box to contents
clears its focus without choosing a fallback. Descendant focus is preserved.
Reveal and scrolling skip the group's empty anchor as a scroll viewport.

### Retained transitions must be reversible

Switching flex → contents → flex preserves identity, listeners, child ownership,
and stored Style. Flattening is a derived layout/paint structure, not reparenting.
Contents has zero effective scroll offset; entering it resets requested scrolling
so a later flex transition does not resurrect a hidden translation. Switching to
none follows existing subtree suppression semantics, rather than flattening it.
Destroying the group still destroys its owned subtree.

### Acceptance checks

Compare a grouped tree's frame and child rectangles with a manually flattened
tree, while asserting different retained parent identities and bubbling paths.
Cover nested contents, none children, absolute descendants, nonzero ancestor
origins and scroll offsets, gaps, cross-sibling z_index, inherited colors,
suppressed owner paint and clipping, focus transitions, selection and hit tests.
Test flex/contents/none transitions, reorder, detach, and destruction separately.

## Consequences

- Contents becomes useful for retained grouping without affecting visible boxes.
- Zero geometry is intentional and cannot be used as a descendant bounding box.
- Layout, paint, hit testing, and focus must agree on box participation; a backend
  display enum alone cannot implement this contract.
- Applying contents to a control suppresses its own rendering and interaction.
  Its separately owned overlays need lifecycle tests before support is claimed.
- Acceptance establishes the contract; runtime implementation and conformance
  tests remain pending.

## Related

- [ADR 0003: Interaction, Focus, and Selection](./0003-define-interaction-focus-and-selection.md)
- [ADR 0007: Scrollbars and Two-Axis Scrolling](./0007-define-scrollbars-and-two-axis-scrolling.md)
- [Layout conformance audit](../layout-conformance-audit.md)
- [OpenTUI ordinary layout options](https://github.com/anomalyco/opentui/blob/ac753b48d386707a931dcf881d0741905b64b4f9/packages/core/src/Renderable.ts#L61-L95)
- [OpenTUI raw display enum](https://github.com/anomalyco/opentui/blob/ac753b48d386707a931dcf881d0741905b64b4f9/packages/core/src/yoga.ts#L37-L41)
