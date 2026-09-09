# Public layout conformance audit

September 9, 2026. Source audit of the current test suite, not a claim that the
gaps below have been filled.

## Cooper defines the contract

Cooper's public Style API, retained operations, and accepted ADRs determine what
must be tested. Tinear provides additional real-application regression evidence;
its feature usage does not determine support or test priority. This work is
valuable independently of any layout-backend replacement.

The audit covers every field of [`Style`](../ui/style.ard), its length and enum
vocabulary, geometry-affecting control composition, and retained transitions.
Color and z-index fields are included to distinguish painting/interaction from
layout. It is not an audit of every non-layout control API.

Evidence labels below:

- **Geometry:** a test asserts a computed dimension or position for a specific
  case. This does not imply complete coverage of that feature.
- **Integration:** rendered cells, hit routes, scroll metrics, or PTY output
  exercise the behavior, sometimes without asserting the complete rectangle.
- **Value:** construction/getter assertions, not behavioral layout evidence.
- **Gap:** no focused behavioral assertion was found in the inspected tests.

Using a property in a fixture does not establish its semantics. Existing
integration coverage should be retained, not dismissed or duplicated wholesale.

## Public feature matrix

| Public surface | Existing evidence | Missing conformance cases |
| --- | --- | --- |
| `width`, `height`: cells | Geometry throughout framework/control tests | Both-axis zero/nonzero transitions; border-box constraints smaller than insets; explicit size versus flex shrink. |
| `width`, `height`: percent | Integration in controls/playground; percentage fixtures are common | Independent non-100% expectations on both axes; nested percentages; odd parent sizes; definite versus indefinite containing dimensions. |
| `undefined`, `auto` lengths | Intrinsic Text geometry and clearing explicit width [S2, F4] | Distinguish auto/undefined/zero where meaningful; measured versus container nodes; auto basis versus explicit dimension. |
| `max_content`, `fit_content`, `stretch` lengths | Gap in focused geometry tests | Available space below/equal/above intrinsic size; finite/indefinite parents; width and height; interactions with min/max and basis. |
| `min_width`, `min_height`, `max_width`, `max_height` | Max-width clamp/reset [S2]; other constraints used in fixtures | Min and max on both axes, percentage and intrinsic forms accepted by validation, min/max conflict policy, flex redistribution after a clamp. |
| `flex_basis` | Value [S1] | Basis overriding width/height; cells/percent/auto/intrinsic basis; indefinite percentages; interaction with min/max. |
| `flex_grow` | One flexible sibling consumes remaining width [F1] | Unequal factors, nonzero bases, zero grow, total factors below one, no positive free space, maximum-size freezing. |
| `flex_shrink` | Value [S1]; many fixtures disable it | Unequal bases and factors, zero shrink, minimum-size freezing, overflow after all items freeze; both main axes. |
| `flex_direction` | Row geometry [F1, F3], column integration; row-reverse PTY [P] | Exact rectangles in all four directions, asymmetric sizes/margins, reverse plus scroll/absolute children; retained order must not change. |
| `flex_wrap` | Ordinary two-line wrap PTY [P] | Exact line-break boundary, wrap-reverse, column wrapping, variable cross sizes, grow/shrink within lines, gap and resize across a wrap threshold. |
| `align_items`, `align_self` | Start/end plus gap in ScrollBox [C1]; center PTY [P]; self is Value [S1] | Auto inheritance, stretch versus definite cross size, per-child overrides, baseline, cross-axis min/max, auto margins overriding alignment. Resolve distribution variants explicitly. |
| `justify_content` | Center/space-between PTY [P] | Exact start/end/center/space-between/space-around/space-evenly coordinates, zero/one/multiple children, negative free space and auto margins. |
| `padding` | Padding reset [F5], border/control composition integration | Four asymmetric edges; percent reference dimension; effect on intrinsic and border-box size; zero and tiny bounds. |
| `margin` | Auto margin is constructed in Value test [S1] | Four asymmetric edges; no collapsing; percentage reference dimension; one/two auto margins with positive and negative free space. |
| `gap` | Vertical gap and reset geometry [C1]; playground integration | Horizontal and wrapped gaps; no leading/trailing gap; percent gaps under definite/indefinite constraints; hidden children. |
| `position`, `top`, `right`, `bottom`, `left` | Absolute left/top with max-width [S2], right/bottom [S3]; overlay PTY [P] | Static ignores offsets, relative offsets preserve sibling flow, absolute nodes excluded from flow, opposing edges with auto/definite size, percentages, containing-block ancestry. |
| `display` | None suppresses paint [F6]; hidden controls excluded from interaction | None removes layout contribution and restores it on show; hidden descendants after previous layout; contents flattening without changing retained ownership. |
| `overflow` | Visible/hidden clipping and hit integration [F7]; two-axis scroll/reveal [F8] | Sizing/measurement differences under scroll; automatic no-shrink policy for immediate children; nested overflow plus intrinsic constraints. |
| `border` | Single border inset, rounded-to-none reset [B] | Same one-cell layout extent for single/double/rounded/heavy, none versus present; asymmetric padding plus border; tiny bounds. Glyph checks remain paint tests. |
| `foreground`, `background`, `border_color` | Box and Text inheritance/paint tests [B, T] | Keep out of solver geometry expectations; verify paint-only changes preserve geometry and that terminal-default versus absence stays distinct. |
| `z_index` | Stable paint/hit order [F9]; overlay PTY [P] | Explicitly preserve flow geometry and public child order while z-index changes. It is not a flex sorting input. |

Length validity is property-specific. Dimension and basis validation accepts all
seven LengthKind variants; min/max rejects auto. Offsets and margins accept
undefined/auto/cells/percent; padding and gap reject auto. Tests must exercise
those public validation boundaries as well as successful layouts, including
directly constructed Style/Length data passed to setters. Invalid values must
not become accidentally accepted just because one helper rejects them earlier.

## Retained behavior and downstream effects

| Transition/consumer | Existing evidence | Additional assertions needed |
| --- | --- | --- |
| Style replacement | Width/max/offset clearing [S2], padding clearing [F5], gap clearing [C1] | Clear every optional geometry group; compare with a fresh tree using the final style. |
| Content/measurement change | Intrinsic Text width and identity [F4]; Unicode wrapping [T] | Changed wrap mode and available width; wrapped height moves following siblings; Input placeholder/value and TextArea private viewport. |
| Resize | Layout playground [P], many control/selection tests | Exact percent/flex/min/max geometry across odd widths and wrap thresholds, narrow→wide→original; compare with fresh layout. |
| Indexed insert/reorder | Exact sibling positions [F3]; attachment-scope tests | Unequal sizes and gaps, reverse/wrapped parents, removing first/middle/last. |
| Detach/reparent | Identity and attachment lifetime [F2]; routing/selection mutation tests | Percentage and intrinsic geometry under differently sized parents; local versus screen coordinates; moving into/out of a scrolling parent changes effective shrink. |
| Hide/show | Paint/focus/hit behavior [F6, F7] | Sibling reflow, zero stale descendant geometry, restoration of measurement after hidden content changes. |
| ScrollBox | Offsets, extents, translated geometry, nested reveal, stable gutters [F8, C1] | Conformance after layout-property changes, not just scrolling fixed-size children. Preserve requested versus effective offsets. |
| TextArea | Wrapping, caret reveal, clipping, internal scrolling, private gutter [A] | Solver-constraint changes must agree with final caret/selection layout; manual scroll must not be undone by unrelated layout. |
| Select popup | Anchoring, stacking, private ownership and callbacks [Q] | Anchor movement/resizing near terminal edges while open, constrained parent and retained overlay geometry. |
| Selection/hit/focus | Substantial integration suites [F7, F8, F9, A, T] | Pair risky new layout cases with the affected cell, clip, hit position or reveal assertion; do not require every layout fixture to duplicate the entire interaction suite. |

## Resolve semantics before freezing expectations

Some publicly accepted values need a more explicit Cooper contract before
golden geometry becomes authoritative:

1. Distribution values (`space_between`, `space_around`, `space_evenly`) in
   `align_items`/`align_self`, where the shared Align enum accepts more than
   conventional item alignment defines.
2. Baseline alignment without a public baseline callback, including container
   baseline selection and column behavior.
3. `Display::contents` interaction with retained local/screen geometry, paint,
   clipping and hit participation; layout flattening alone is not sufficient.
4. Intrinsic keyword constraints, percentage resolution under indefinite sizes,
   wrapped-line cross distribution, and fractional cell-rounding policy.

Investigate existing backend behavior as evidence, then state the intended public
rule. Do not silently make unsupported enum combinations panic, remove public
values, or bless every Yoga fallback. Intentional contract changes need an ADR;
backend bugs should not be copied into expected results.

## Test design and order

First add public-API tests to the existing style/framework/control test owners;
use TestApp for observable frames and detached Runtime for isolated geometry.
No backend-switching abstraction or serialized fixture format is needed merely
to strengthen Cooper's tests.

Prioritize independent arithmetic cases before ambiguous semantics:

- With shrink disabled and no spacing, three zero-basis children in a 60-cell
  row growing in ratio 1:2:3 must occupy 10/20/30 cells. A max-width of 16 on
  the second redistributes the remaining 44 cells in ratio 1:3, producing
  11/16/33. These exact divisions isolate redistribution from rounding.
- Bases 80 and 40 with equal shrink in a 90-cell row become 60 and 30. A
  minimum of 70 on the first redistributes to 70 and 20. Equal subtraction or
  clamp-only implementations fail these inputs.
- Widths 3 and 5 in a 20-cell row distinguish justification modes. Add margins
  and a gap only in separate cases so a failed expected position has one cause.
- Use parent dimensions 40×20 for asymmetric percentages, then odd dimensions
  for dedicated rounding cases. Square parents hide wrong-axis percentage bugs.
- Change an intrinsic Text from one row to several wrapped rows and assert the
  following sibling's position, not merely the text's own dimensions.
- For mutation tests, assert independently calculated final geometry and compare
  it with a fresh tree. Fresh-tree equivalence alone can reproduce a shared bug.

Then add targeted interaction cases and documented semantics from the preceding
section. Seeded valid-tree/property testing is useful for invariants and mutation
equivalence, but does not replace independently derived examples. Test both sides
of boundaries rather than increasing counts of trivial layouts.

Completion means every supported variant has a behavioral assertion, every
identified ambiguity has an explicit decision, and the high-risk interactions
and retained transitions above are covered. It does not mean exhaustively
enumerating the Cartesian product of all Style fields. Existing compiler,
formatter, Ard/Go, headless and PTY checks remain required when tests or behavior
are changed. Tinear is an additional consumer check, never the completion gate
for Cooper's public feature matrix.

## Evidence index

Names refer to existing tests at audit time; proposed cases above are not yet
implemented.

- **S1–S3:** [`test/style_test.ard`](../test/style_test.ard):
  `style_new_configures_the_complete_public_vocabulary`,
  `style_replacement_clears_dimensions_constraints_and_offsets`,
  `absolute_edge_offsets_reach_the_layout_backend`.
- **F1–F6:** [`test/framework_test.ard`](../test/framework_test.ard):
  `retained_tree_mirrors_explicit_children_into_yoga`,
  `retained_remove_detaches_and_readd_preserves_identity`,
  `retained_indexed_add_inserts_and_reorders_in_final_order`,
  `retained_text_measurement_updates_without_rebuilding_identity`,
  `retained_style_replacement_clears_spacing`,
  `retained_display_none_skips_paint`.
- **F7:** same file: `retained_hit_testing_uses_layout_viewport_for_visible_overflow`,
  `retained_hit_testing_obeys_ancestor_clipping`,
  `retained_node_overflow_clips_its_own_paint`.
- **F8:** same file: `retained_scroll_translates_clips_paint_and_hit_geometry`,
  `retained_horizontal_scroll_translates_clips_paint_and_hit_geometry`,
  `retained_scroll_preserves_requested_offset_across_layout_changes`,
  `retained_nested_scroll_reveal_settles_inside_out`.
- **F9:** same file: `retained_z_index_controls_stable_paint_and_hit_order`.
- **B:** [`test/box_test.ard`](../test/box_test.ard), especially
  `box_paints_background_border_title_and_insets_children` and
  `box_decoration_setters_update_layout_and_common_api`.
- **C1:** [`test/scroll_box_test.ard`](../test/scroll_box_test.ard):
  `scroll_box_preserves_public_child_gap_and_alignment_through_viewport`.
- **T:** [`test/text_test.ard`](../test/text_test.ard), particularly Unicode word
  wrapping, complete-grapheme character wrapping, and color inheritance tests.
- **A:** [`test/text_area_test.ard`](../test/text_area_test.ard), especially
  `text_area_wraps_exact_width_and_keeps_trailing_cursor_visible`,
  `text_area_private_scrollbar_composition_respects_public_padding`, and
  `manual_text_area_scroll_does_not_reveal_hidden_caret_in_parent`.
- **Q:** [`test/select_test.ard`](../test/select_test.ard).
- **P:** [`examples/test_layout_playground.py`](../examples/test_layout_playground.py).
