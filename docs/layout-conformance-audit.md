# Public layout conformance audit

September 10, 2026. The original September 9 source-audit matrices below are
preserved as a baseline. The integration evidence here records which gaps now
have additional tests, without claiming complete conformance.

## Initial Ard replacement: current evidence and remaining work

`core/node.ard` now computes layout through `core/layout.ard`, not the Go Yoga
adapter. Ard owns sizing, flex allocation, positioning, and cell projection.
The numeric bridge only widens Float32 values because the current Ard API lacks
that conversion. The unused Yoga adapter and dependency remain in the repository
for now; this is an implementation milestone, not a completed backend retirement.

All nine failures in the historical ADR 0016 table below now pass, including the
assertions previously unreachable after each first failure. `max_content` Text
`abc defgh` in a five-cell parent is 9×1, and bordered/padded multiline Text is
9×6. Text uses the Node's committed local content rectangle for wrapping, paint,
clipping, links, cursor placement, and selection. Its border resets with Style.

Additional regressions distinguish independently allocated stretch width from
an equal natural width, measured/unmeasured edge rounding, zero-height text
after flex shrinking, and auto versus explicit absolute offsets inside borders.
These are targeted cases, not complete acceptance coverage for ADR 0020.

Two PTY expectations needed deliberate migration away from Yoga's text-specific
rounding. The gallery's character sample has 11 cells instead of 12; its test
checks the new split and preserves complete-source assertions for both ordinary
and long-token samples. In the 50×12 TextArea fixture, fixed editor height left
the status only 1/3 of a row, whose edges both project to row 11. The fixture now
lets the editor shrink and makes title/status nonshrinking. The headless test
`cell_projection_can_collapse_shrunk_text_like_an_unmeasured_box` preserves the
zero-height rule instead of adding an implicit one-cell Text minimum.

Verification:

- `ard test`: **321 passed; 0 failed; 0 panicked**, including all 299 checkpoint
  tests, 16 intrinsic-contract tests, three Text border tests, two projection
  tests, and one absolute-default-origin test.
- `ard format`, `ard check`, and `ard format --check` passed for all seven changed
  Ard files, including the new engine and the TextArea fixture.
- `go test ./...`: all seven tested packages passed; retainedyoga has no tests.
- All 20 PTY entry points listed in `AGENTS.md` passed. Layout/Select checks were
  rerun after the final absolute-default-origin correction.
- `python3 benchmarks/run.py --iterations 3 --warmups 1` completed every case.
  This was a smoke run concurrent with PTY tests, not a comparative performance
  claim. Dirty-layout caching and a controlled old/new comparison remain pending.
- Inspected `text-border-states.png` (headless Frame visualization) and
  `text-area-layout.png` (captured PTY text, empty and edited states). These are
  cell-content visualizations, not native terminal color/cursor screenshots.

**The port is not yet fully conformant to the accepted ADRs.** Remaining work:

- ADR 0016: broaden intrinsic constraints/basis, percentage bounds and spacing,
  and independently definite versus content-derived allocation coverage on both
  axes. Passing the 16 cases does not establish all combinations.
- ADR 0017: add `align_content`, property-specific validation, and wrapped-line
  distribution tests. Current wrapped lines only use stretch distribution.
- ADR 0018: implement and test bottom-border-edge baseline groups with margins;
  the initial engine does not implement that baseline policy.
- ADR 0019: complete boxless retained geometry, paint/stacking, hit/focus,
  scrolling, inheritance, and transitions. Layout flattening alone is insufficient.
- ADR 0020: reconcile width-dependent measurement with projected cell width
  before committing dependent heights. Edge projection is implemented, but the
  full measurement/projection convergence contract is not.

The sections below retain the earlier Yoga baseline and initial failing-test
evidence; their counts are historical, not the current test result.

## Integrated conformance baseline

Integrated 32 additional tests from the test sub-thread: 24 Style tests, five
retained-framework tests, and one each for ScrollBox, Input, and TextArea.
Its Select regression was already integrated with the popup anchoring fix;
the additional parent-layout/height-resize regression remains intact. The moved
anchor assertion now also checks that the owner's height remains one cell.

| Test owner | Added coverage |
| --- | --- |
| [Style](../test/style_test.ard) | Independent grow ratios, fractional total grow, weighted shrink and bound freezing on both axes; explicit/percent/auto basis; asymmetric percentages and constraints; all Justify modes; item inheritance, overrides, stretch and auto margins; percentage spacing; reverse/wrap/reorder; static/relative/absolute containing blocks; border insets/reset; direct malformed length/factor validation and each spacing edge. |
| [Framework](../test/framework_test.ard) | Hidden subtree reflow, focus/hits and changed hidden measurement; wrap/resize-dependent sibling geometry; percent reparent and screen coordinates; scroll-parent shrink policy without public Style mutation; complete Style reset and paint-only updates. |
| [ScrollBox](../test/scroll_box_test.ard) | Gap reset and hidden rows update extents, effective/requested offsets, translated paint and hit routing. |
| [Input](../test/input_test.ard) | Value/placeholder/caret-room measurement and max-width/reset move following siblings; fresh-control comparison. |
| [TextArea](../test/text_area_test.ard) | Percentage resize, private scrollbar gutter, exact-width trailing caret rows and fresh-frame comparison. |
| [Select](../test/select_test.ard) | Open menu follows owner movement, sibling growth and terminal resize in the same frame; old cells clear and relocated menu rows remain clickable. |

The only production change in this integration parenthesizes three `not finite`
checks in `ui/style.ard`. Current Ard parses `not finite(x) or x < 0` as
`not (finite(x) or x < 0)`, which accepted negative directly constructed lengths
and flex factors. The imported setter tests enforce the existing non-negative
contract, including rejection without replacing the previous public Style.

The worker's assertion that broad item-alignment distribution values are
accepted was deliberately not integrated: it contradicts accepted ADR 0017.
No runtime alignment validation change is included in this baseline step.
Intrinsic keyword setter acceptance remains value-only evidence, not proof of
the geometry required by ADR 0016. No 5×2 max-content fallback was made a golden.
Exact arithmetic tests do not establish ADR 0020's fractional rounding contract.

Verification in the combined checkout:

- `ard test`: **299 passed; 0 failed; 0 panicked** (267 before integration).
- `ard format`, `ard check`, and `ard format --check` passed for `ui/style.ard`
  and the six affected test files listed above.
- `go test ./...`: seven packages passed; retainedyoga has no Go tests.
- From `examples/`, `python3` passed each of `test_layout_playground.py`,
  `test_scroll_form.py`, `test_horizontal_scroll.py`, `test_text_gallery.py`,
  `test_input_lab.py`, `test_text_area.py`, `test_select.py`, and
  `test_interaction.py`.

These results establish a passing current-backend baseline. The accepted ADRs
remain the specification for subsequent contract tests and the Ard replacement;
passing this suite alone does not establish conformance to all five decisions.

## ADR 0016 executable contract cases

After the passing checkpoint, 15 `intrinsic_contract_*` tests were added to
`test/style_test.ard`. Expected rectangles come from ADR 0016, not backend
snapshots. They run in the ordinary suite without skips or expected-failure
wrappers. Each test destroys its detached Runtime even when an assertion fails.

Full `ard test`: **305 passed; 9 failed; 0 panicked**. All 299 baseline tests
still pass; six new contract tests pass and nine expose current implementation
gaps. `ard format`, `ard check`, and `ard format --check` pass for the changed
test file. Run just this group with `ard test --filter intrinsic_contract`.

| Failing case (test suffix) | Required width×height | Observed width×height |
| --- | --- | --- |
| `max_content_overflows_narrow_parent` | 9×1 | 5×2 |
| `stretch_fills_available_width_minus_margins` | 14×1 at (3,3) | 3×1 at (3,3) |
| `height_preserves_finite_width_wrapping` | 5×2 | 5×1 |
| `explicit_width_is_not_alignment_stretch` | 9×1 | 20×1 |
| `explicit_lines_and_insets_count_once` | 9×6 | 7×4 |
| `max_content_minimum_prevents_shrink` | 9×1 | 3×4 |
| `max_content_bound_limits_explicit_width` | 9×1 | 20×1 |
| `basis_overrides_conflicting_preferred_width` | 9×1 | 3×4 |
| `container_natural_width_ignores_soft_wrap_and_out_of_flow` | 9×2 | 5×4 |

Passing cases cover fit-content below/equal/above natural width with a long word
(no CSS min-content floor); max-width remeasurement and reset moving a following
sibling; widest explicit line; minimum-over-maximum precedence on both axes;
physical inset floors; and an indefinite percentage that stays content-sized
until an independently definite parent width becomes available.

The Text inset failure is not solely a Yoga keyword issue: `Node` stores border
width separately from Style, and `Box` calls `set_border_width` while `Text`
does not. The plain explicit-lines case passes. The accepted Text border-box
example therefore requires Cooper integration work as well as sizing changes.

Assertions following the first failure in the basis and container tests are not
reached; their sibling/child coordinates are requirements, not verified evidence.
This is initial ADR 0016 coverage, not full conformance: remaining combinations
include fit/stretch intrinsic constraints and basis, indefinite percentage bounds
and spacing, Unicode/zero-size keyword cases, and broader retained mutations.
ADRs 0017–0020 also require their own contract tests. No solver or runtime behavior
was changed in this test-only step, and no fallback was blessed to keep it green.

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

[Accepted ADR 0016](./adrs/0016-define-intrinsic-sizing-and-constraints.md)
specifies intrinsic dimensions, constraint precedence, flex basis and indefinite
percentage resolution. The remaining decisions have accepted contracts:

- [ADR 0017](./adrs/0017-define-item-alignment-and-line-distribution.md):
  property-specific alignment validity and explicit wrapped-line distribution.
- [ADR 0018](./adrs/0018-define-baseline-alignment.md): deterministic bottom-edge
  box baselines rather than implicit descendant selection.
- [ADR 0019](./adrs/0019-define-display-contents.md): boxless layout/paint
  participation with retained ownership and event ancestry.
- [ADR 0020](./adrs/0020-define-layout-cell-rounding.md): shared absolute-edge
  rounding, half-tie policy, and measured-content reconciliation.

ADRs 0016–0020 are Accepted, with runtime implementation
and conformance tests pending. Their acceptance-check sections describe required
future coverage, not tests already passing today.

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
