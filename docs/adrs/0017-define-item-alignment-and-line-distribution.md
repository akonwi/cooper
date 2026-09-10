# 0017: Define Item Alignment and Wrapped-Line Distribution

## Status

Accepted

## Context

Cooper exposes one `Align` enum for `align_items` and `align_self`, including
distribution values that describe groups of lines rather than individual items.
It exposes wrapping but no `align_content`. Passing these values through to
Yoga does not give applications a clear, replaceable contract.

OpenTUI also exposes a broad shared alignment vocabulary and no ordinary
renderable `alignContent` property. Its raw Yoga API has that property, but this
is not a documented renderable-level line-distribution contract. Cooper should
make these responsibilities explicit rather than inherit backend fallbacks.

## Decision

### Separate items from lines

Keep `Align` for source compatibility, but validate values by property when
applying a Style. Constructors remain infallible value constructors.

| Property | Supported values | Default |
| --- | --- | --- |
| `align_items` | start, end, center, stretch, baseline | stretch |
| `align_self` | auto, start, end, center, stretch, baseline | auto |
| New `align_content` | start, end, center, stretch, space_between, space_around, space_evenly | stretch |

`align_self: auto` inherits `align_items`. Reject `align_items: auto`, item
distribution values, and `align_content: auto/baseline` as programmer contract
violations. This is an intentional tightening of accepted Style values, not a
claim that these combinations were already validated. Applications using item
distribution values must choose item alignment or move distribution to
`align_content`; these are different effects.

Item alignment positions each item's margin box within its line's cross extent.
Stretch applies only to auto cross sizes, subject to min/max constraints;
explicit cross sizes remain unchanged. Start/end follow the cross-axis direction,
including its reversal under `wrap_reverse`. Main-axis reverse does not reverse
the cross axis. Baseline is specified separately in ADR 0018.

```diagram
row line, height 4; item height 2

start          center         end            stretch (auto height)
┌──────┐       ┌──────┐       ┌──────┐       ┌──────┐
│ AA   │       │      │       │      │       │ AA   │
│ AA   │       │ AA   │       │      │       │ AA   │
│      │       │ AA   │       │ AA   │       │ AA   │
│      │       │      │       │ AA   │       │ AA   │
└──────┘       └──────┘       └──────┘       └──────┘
```

### Distribute lines independently of items

For `no_wrap`, the single line fills the available inner cross extent and
`align_content` has no effect. For wrapping, first compute each line's natural
cross extent, including item margins and baseline requirements. Subtract those
extents and configured cross-axis gaps from the container's inner cross extent
to obtain free space. An indefinite cross extent supplies no extra free space.

With positive free space: start/end/center offset the group; space_between divides
space between lines; space_around gives each line equal space on both sides;
space_evenly gives every outer and inter-line space an equal share. Existing
gaps are minimum separations, with distribution added to them. Stretch divides
free space equally among line extents, then applies item alignment within each
expanded line. It does not stretch explicitly sized items.

```diagram
cross extent 10; two lines of extent 2; gap 0

align_content        line starts       line extents
start                0, 2              2, 2
end                  6, 8              2, 2
center               3, 5              2, 2
space_between        0, 8              2, 2
space_around         1.5, 6.5          2, 2
space_evenly         2, 6              2, 2
stretch              0, 5              5, 5

Logical cross start ─────────────────────▶ cross end
wrap_reverse mirrors these positions; tree order stays unchanged.
```

With one wrapped line, space_between behaves as start; space_around and
space_evenly center it. With negative free space, stretch and space_between
fall back to start, and space_around/space_evenly fall back to center. End and
center may overflow before cross-start; they are not implicitly safe alignment.
Zero free space adds no distribution. Overflow clipping remains independent.
Round only after allocation, as specified in ADR 0020.

### Acceptance checks

Test every property/value validity boundary. Use asymmetric line sizes and
explicit versus auto cross sizes to distinguish item stretching from line
stretching. Cover row/column, reverse/wrap_reverse, one and multiple lines,
nonzero gaps, indefinite cross size, and positive/zero/negative free space.
Compare retained style changes with independently calculated fresh layouts.

## Consequences

- Line distribution becomes publicly controllable rather than a backend default.
- This decision adds one Style field and rejects ambiguous existing combinations;
  implementation requires migration notes and validation tests.
- Item, line, and main-axis distribution have separate responsibilities.
- Acceptance establishes the contract; runtime implementation and conformance
  tests remain pending.

## Related

- [ADR 0016: Intrinsic Sizing and Constraints](./0016-define-intrinsic-sizing-and-constraints.md)
- [ADR 0018: Baseline Alignment](./0018-define-baseline-alignment.md)
- [ADR 0020: Cell Rounding](./0020-define-layout-cell-rounding.md)
- [Layout conformance audit](../layout-conformance-audit.md)
- [OpenTUI layout options](https://github.com/anomalyco/opentui/blob/ac753b48d386707a931dcf881d0741905b64b4f9/packages/core/src/Renderable.ts#L61-L95)
- [OpenTUI alignment vocabulary](https://github.com/anomalyco/opentui/blob/ac753b48d386707a931dcf881d0741905b64b4f9/packages/core/src/lib/yoga.options.ts#L19-L97)
