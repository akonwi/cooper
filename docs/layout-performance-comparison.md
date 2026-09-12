# Ard layout comparison: September 12, 2026

The translated engine now replaces Tess in production. Performance remains
mixed; this is not a performance-parity claim. The original measurements below
describe the independent solver that has since been removed. Final translated
engine results are recorded at the end of this document.

For the subsequent controlled comparison against fetched `origin/main`, CPU
profiles, allocation measurements and versioned raw samples, see the
[profiling baseline](./layout-profiling-baseline.md).

## Method

Compared the original Yoga checkpoint
[`650013d`](https://github.com/akonwi/cooper/commit/650013dc9525c504b42089cb5c30ddd54e3c5ff0)
with the Ard checkpoint
[`505f8d3`](https://github.com/akonwi/cooper/commit/505f8d3)
and then its uncommitted fixed-leaf measurement optimization. Both checkouts used
the same installed Ard compiler and Go 1.27.0, Linux/amd64, in this orb.

`benchmarks/compare.py` checks that benchmark source files are byte-identical,
builds each separately, runs one warmup per binary and nine measured samples,
and alternates which backend runs first. It checks all reported non-timing
observations for equality. All those checks passed. The raw JSON records source
hashes, compiler version, revisions, and samples; the optimized run additionally
records tracked-diff hashes. Existing `backend=tess_*` strings in benchmark
output are legacy workload labels, not evidence of which engine ran.

Reproduce with an isolated baseline worktree:

```sh
git worktree add --detach /tmp/cooper-yoga-baseline 650013dc9525c504b42089cb5c30ddd54e3c5ff0
python3 benchmarks/compare.py /tmp/cooper-yoga-baseline . \
  --samples 9 --warmups 1 --output /tmp/layout-comparison.json
```

These are same-orb comparisons, not pinned-CPU laboratory results. GC,
scheduling and shared-host noise remain. Nine samples support medians and ranges,
not a reliable tail-latency percentile. Render timings include layout, retained
geometry, reconciliation, painting and allocation; they do not isolate the
solver. The checkpoints also differ in retained/control semantics, so not every
timing difference is attributable to the layout engine.

## Render medians after skipping unused fixed-leaf measurement

All values are microseconds. The last column is candidate/baseline; smaller is
better. It describes the measured run, not a guaranteed speedup.

| Workload | Yoga | Ard | Ratio |
| --- | ---: | ---: | ---: |
| 1,001-node initial render | 41,678 | 42,475 | 1.02× |
| 1,001-node single update | 22,512 | 20,636 | 0.92× |
| 1,001-node resize | 8,756 | 6,640 | 0.76× |
| Virtual-list initial render | 447 | 534 | 1.19× |
| Virtual-list scroll jump | 520 | 579 | 1.11× |
| Virtual-list single-row update | 466 | 2,171 | 4.66× |
| Virtual-list window shift | 547 | 684 | 1.25× |
| Virtual-list resize | 1,045 | 678 | 0.65× |
| Virtual-list unchanged render (`paint_us`) | 406 | 850 | 2.09× |
| 1,000 attach/detach/render cycles | 162,602 | 157,816 | 0.97× |
| Deep-tree initial render | 360 | 251 | 0.70× |
| 1,000 deep-tree renders | 229,750 | 301,739 | 1.31× |
| 100×200 selection workload | 775,584 | 912,769 | 1.18× |

Before this optimization, the virtual-list initial/jump/shift medians were
1,045/2,438/1,280 µs respectively. The optimized run measured 534/579/684 µs.
However, the single-row update median moved from 1,197 to 2,171 µs, illustrating
why these separate runs do not justify a universal improvement claim.

The optimization skips the measure callback only when both dimensions are
already resolved after intrinsic constraints. Its deterministic regression made
six callbacks across three fixed-leaf layouts before the change and zero after;
intrinsic bounds and auto height continue to measure and preserve geometry.

## Layout-only measurement exposes the remaining reuse problem

`benchmarks/layout_only.ard` uses a detached Runtime, 64 measured leaves, and
1,000 calls per phase. It includes solver and retained geometry synchronization,
but no painting, frame allocation, focus, or selection reconciliation. Identical
source was copied to the baseline checkout, built with the same compiler, and
run with the same nine-sample alternating protocol. Each run asserts the
updated leaf's final 41×1 geometry after all three phases.

| Leaf sizing / 1,000 layouts | Yoga µs | Ard µs | Yoga callbacks | Ard callbacks |
| --- | ---: | ---: | ---: | ---: |
| Fixed dimensions, unchanged | 13,383 | 27,839 | 0 | 0 |
| Fixed dimensions, one width update | 38,757 | 26,945 | 0 | 0 |
| Fixed dimensions, root resize | 35,602 | 25,453 | 0 | 0 |
| Auto height, unchanged | 12,715 | 25,939 | 0 | 192,000 |
| Auto height, one width update | 46,782 | 26,065 | 1,000 | 192,000 |
| Auto height, root resize | 43,510 | 25,680 | 0 | 192,000 |

The callback deliberately returns a cheap constant natural size. These timings
therefore understate the cost of repeatedly measuring real rich text. The counts
are deterministic evidence independent of timing noise: Ard repeatedly visits
all 64 leaves and measures them three times per layout. Yoga reuses unchanged
measurements; a width update only measures the affected leaf once.

## Next performance work

Keep the unused Yoga bridge/dependency as a reference. Follow the
[Yoga-to-Ard port map](./yoga-ard-port-map.md): translate Yoga's node state,
invalidation, cache compatibility and recursive layout phases rather than add
a bespoke cache to the independent solver. Preserve accepted ADR behavior as
explicit adaptations, including transaction-local projected-width replay that
cannot contaminate natural measurements. Verify changed content and resize
cycles against fresh layouts, then repeat both render and layout-only
comparisons. Memory allocation and real-consumer performance still need
measurement; no frame budget has been agreed or proven here.

Raw data is available in this thread's artifacts:
`layout-comparison.json`, `layout-comparison-fixed-measurement.json`, and
`layout-only-comparison.json`.

## Final translated engine

The same nine-sample, alternating-order comparison passed all non-timing
observations after production integration. Representative median times:

| Workload | Tess/Yoga µs | Ard µs | Ard / native |
| --- | ---: | ---: | ---: |
| 1,001-node initial layout | 25,416 | 27,367 | 1.08× |
| 1,001-node single update | 19,711 | 16,205 | 0.82× |
| Virtual-list single-row update | 424 | 1,439 | 3.39× |
| Virtual-list resize | 936 | 569 | 0.61× |
| Virtual-list paint | 445 | 1,082 | 2.43× |
| 1,000 attach/detach/layout cycles | 168,674 | 161,064 | 0.95× |

Timings were collected in the development orb alongside verification activity;
they are diagnostic rather than a controlled performance budget. Virtual-row
updates and painting merit profiling. No new public contract is needed for that
optimization work, and no speed parity is claimed.

The layout-only workload now reports these deterministic callback counts over
1,000 transactions (final geometry remains 41×1):

| Leaf dimensions | Unchanged | One width update per transaction | Root resize |
| --- | ---: | ---: | ---: |
| Fixed width/height | 0 | 0 | 0 |
| Fixed width, auto height | 0 | 1,000 | 0 |

These match the original native counts and replace the independent solver's
192,000 callbacks per auto-height phase. A headless regression separately checks
that content invalidation triggers a fresh callback and changes geometry, while
an unchanged transaction or compatible root resize reuses the measurement.

Final render comparison data: `.amp/in/artifacts/layout-port-comparison.json`.
The optional native comparison fetches Tess through its historical baseline;
production modules and builds no longer depend on it.
