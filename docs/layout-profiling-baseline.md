# Layout profiling baseline against main — September 12, 2026

## Revisions and protocol

Baseline: fetched `origin/main`, also equal to local `main`, at
[`650013d`](https://github.com/akonwi/cooper/commit/650013dc9525c504b42089cb5c30ddd54e3c5ff0)
(Tess/Yoga). Candidate: `ard-native-layout` at
[`a9e1543`](https://github.com/akonwi/cooper/commit/a9e1543a85f94a20fabdfd6d5f7ee682306afa4d).
No production performance changes were made during this investigation.

Both ran in the same Linux/amd64 orb with two available CPUs, Go 1.27.0 and
the same Ard compiler. `ard version` reports `dev`; its Go build metadata
identifies clean compiler revision
[`3fd6267`](https://github.com/akonwi/ard/commit/3fd626729f1e5be16d6bd074dc5f900060861f63).
GC and parallelism settings were left at defaults. Benchmarks and profiles ran
sequentially, without concurrent test suites or builds. Orb timings remain
machine-specific observations, not release gates or performance guarantees.

Two complementary experiments:

1. **Repeated isolated operations:** identical new Ard fixture on both revisions;
   25 samples of 1,000 operations, alternating branch order, after three process
   warmups. Every process initializes its tree, runs ten warmup operations and
   forces GC before timing. Setup, validation and destruction are excluded.
   Layout-only uses 64 fixed-size Text rows. Rendering uses 64 retained rows in
   a scrolled 10,000-row logical list, including spacers and a ScrollBox.
2. **Existing retained scenarios:** all four byte-identical benchmark sources;
   25 samples, three warmups, alternating branch order. These preserve their
   existing sequential initial-render/jump/update/resize/paint timing boundaries.

CPU profiles run separately, targeting approximately five seconds of operations
per branch/phase. Allocation profiles use 4 KB Go sampling and subtract a
post-setup profile. Exact allocation deltas come from unprofiled `MemStats`
batches. All fixture geometry/frame assertions and existing comparison
observations passed. See [reproduction commands](../benchmarks/README.md#main-branch-baseline-and-profiling).

## Repeated operations: a modest update slowdown and much cheaper unchanged layout

Times are microseconds per operation. Parentheses show p95 of the **batch
averages**, not individual-operation or frame-latency p95.

| Operation | main median (p95) | Ard median (p95) | Ard/main |
| --- | ---: | ---: | ---: |
| Layout: one row content update | 37.28 (43.84) | 35.40 (40.83) | 0.95× |
| Layout: unchanged | 15.51 (17.09) | 0.79 (0.83) | 0.05× |
| Full render: one visible row update | 385.31 (435.62) | 413.40 (455.28) | 1.07× |
| Full render: unchanged | 350.65 (380.91) | 332.85 (375.69) | 0.95× |

`render_unchanged` still forces a complete headless render, including layout
dispatch, focus/selection reconciliation and painting. It is not a skipped frame
or an isolated paint-only API. The two layout tests omit painting entirely.

| Operation | main Go bytes/op | Ard Go bytes/op | main allocations/op | Ard allocations/op |
| --- | ---: | ---: | ---: | ---: |
| Layout: update | 297 | 40,748 | 6 | 193 |
| Layout: unchanged | 0 | 0 | 0 | 0 |
| Render: update | 536,244 | 606,150 | 1,863 | 2,188 |
| Render: unchanged | 534,718 | 534,745 | 1,826 | 1,830 |

These are **Go heap traffic**, not peak/resident memory. They exclude native
Yoga/C++ allocations, so they cannot establish total-memory superiority of
either backend. They do establish new Go GC pressure in the port's dirty-layout
path, and a shared allocation-heavy rendering path.

## Profiles locate the new layout cost and the shared rendering cost

**Horizontal snapshots and temporary flex lists are the first port-specific
targets.** In the candidate layout-update allocation profile:

- `Node.freeze_horizontal`: about 32.7% of sampled allocation bytes and 12.0%
  cumulative CPU samples.
- `visitor.translated_visit`: 28.7% flat allocation bytes.
- `flex.collect_line`: 22.5% flat allocation bytes.
- Child preparation/flattening: about another 10% flat allocation bytes.

The source currently snapshots every node's horizontal state and copies its
cache before checking whether projected widths require replay. Even integral
trees incur this allocation. The visitor also creates temporary child, item,
line, extent and distribution lists on each dirty transaction. The profile
supports investigating these allocations; it does not prove a particular
optimization's speedup in advance.

**Fresh paint buffers dominate allocation on both branches.** On updated
renders, `paint.new_buffer` accounts for approximately 447–448 MB allocated over
1,000 operations on each branch: 87.4% of main's sampled bytes and 77.3% of the
candidate's. It takes 24.9% and 29.1% cumulative CPU samples respectively.
`runtime.draw` allocates a new buffer each frame; `new_buffer` grows an initially
empty cell list. Candidate unchanged rendering still spends 28.0% cumulative
CPU samples in buffer construction.

**Text painting also repeats glyph work on unchanged frames.** Vaxis character
segmentation contributes roughly 51–52 MB per 1,000 renders on both branches.
In candidate unchanged-render CPU samples, `Text.paint` accounts for 31.3%
cumulatively; `vaxis.Characters` accounts for 14.3%. This is existing shared
work, not evidence that the translated layout engine itself is slow.

Cumulative CPU percentages overlap through call stacks and include background
GC; do not add them. Sampled allocation reports include roughly 1 MB of
profiling-writer overhead, which is not attributed to framework operations.

## The original scenario still exposes larger isolated spikes

These are medians from the unchanged retained benchmarks, in microseconds.
They are intentionally preserved as a separate baseline from warm steady-state
operations.

| Scenario metric | main | Ard | Ard/main |
| --- | ---: | ---: | ---: |
| 1,001-node initial layout/render | 43,585 | 49,191 | 1.13× |
| 1,001-node single update/render | 20,819 | 20,493 | 0.98× |
| 1,001-node resize | 7,676 | 6,620 | 0.86× |
| Virtual-list initial render | 474 | 486 | 1.03× |
| Virtual-list single-row update after jump | 487 | 1,503 | 3.09× |
| Virtual-list window shift average | 544 | 529 | 0.97× |
| Virtual-list resize | 544 | 485 | 0.89× |
| Virtual-list render after resize (`paint_us`) | 870 | 1,340 | 1.54× |
| 1,000 attach/detach/layout cycles | 174,626 | 165,341 | 0.95× |
| Deep initial layout | 349 | 592 | 1.70× |
| 10,000 deep hit tests | 1,156,270 | 1,258,520 | 1.09× |
| 1,000 deep paints | 250,765 | 245,897 | 0.98× |
| 10,000 overlapping hit tests | 16,845 | 19,278 | 1.14× |
| 100 selections through 200 nodes | 797,082 | 895,906 | 1.12× |

The 3.09× single-update result is reproducible in this scenario and must not be
dismissed because repeated updates are only 1.07×. The tests exercise different
history, heap state and warmup. Extra allocation/GC is a plausible contributor,
but a trace spanning that exact jump→update boundary is needed before attributing
the entire spike to GC. No individual-frame tail-latency claim is established.

## Optimization order and regression criteria

1. Avoid horizontal/cache snapshots when replay is unnecessary. Preserve the
   projected-width, natural-cache and frozen-line tests; compare dirty-layout
   bytes/op as well as time.
2. Reduce per-transaction flex scratch allocation while retaining translated
   phase semantics. Recheck both shallow updates and deep initial layout.
3. Allocate paint buffers at their required size, then evaluate safe reuse.
   Reuse must preserve the lifetime of previously returned headless frames.
4. Investigate repeated text segmentation/measurement during unchanged painting.
   Preserve wide-glyph clipping, links, selections and caret behavior.
5. Trace the original jump→single-update and resize→render boundaries to verify
   whether improvements also remove their spikes, not just warm averages.

Do not set universal time thresholds from one orb run. Compare revisions on the
same machine with identical fixtures, examine allocation counts and distributions,
and retain both experiments. Optimizations are follow-up work, not part of this
baseline checkpoint.

## Saved evidence

Generated evidence is no longer stored in the working tree. The
[archived baseline directory](https://github.com/akonwi/cooper/tree/e100649ecb4f83740fbcceab13cd701f37d4fe43/benchmarks/baselines)
contains `main-2026-09-12-profile.json` (repeated samples) and
`main-2026-09-12-retained.json` (scenario samples). See the
[benchmark guide](../benchmarks/README.md) for retrieval and reproduction.

Raw JSON includes exact Cooper revisions, fixture hashes and all samples. The
profiling fixture and Go driver are benchmark-only additions; they do not change
the production backend or make its native baseline use the candidate's solver.
