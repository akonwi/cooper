# Complex feed benchmark

## A nested scrolling workload, not a complete application

Inspired by Flutter's actual
[`complex_layout`](https://github.com/flutter/flutter/tree/master/dev/benchmarks/complex_layout)
benchmark and its
[down/up scroll driver](https://github.com/flutter/flutter/blob/master/dev/benchmarks/complex_layout/test_driver/scroll_perf_test.dart).
This is an original terminal fixture borrowing the workload shape, not copied
Flutter source or assets, and not a numerical comparison with Flutter.

The fixed 100×36 screen contains:

- A two-row header and footer around a 32-row ScrollBox.
- 500 logical cards alternating between short and long content.
- Wrapped descriptions, nested three-tile gallery rows, metadata and actions.
- Natural card heights of 12 and 17 cells, checked against the virtualization
  index at setup and for every mounted card after each interaction.
- A lazy eight-card window with top/bottom spacers. Overlapping cards retain
  their objects; cards leaving the window are removed and recursively destroyed.
- An eager 500-card mode with identical content, serving as an independent
  full-tree correctness reference and an intentionally expensive control.

The virtualized height index is deliberately fixture-specific and only valid
at this viewport/content. Gallery tiles use 28-cell widths to avoid the
intentional native/ADR0020 fractional rounding difference; the first comparison
caught a one-cell tile-position difference with 30% widths. We changed the
fixture, not either engine or the equality check. The main conformance suite
continues to cover fractional geometry.

Each session scrolls down 20 times by 37 cells (offset 740, entry 51), then up
20 times, returning to the top. This crosses many window boundaries instead
of just scrolling inside an initially mounted set. The fixture does not yet
cover resize, editing, popups, async update scheduling, or terminal I/O. Those
belong in a later stateful reference screen if a concrete performance question
requires them. The footer is illustrative chrome, not a live keyboard binding.

## Correctness gates precede any performance conclusion

At every step, assertions check the requested/effective scroll position, fixed
chrome, card heights, visible card position, and the lazy mount bound. The runner
compares a SHA-256 digest of complete frame text plus scroll offset and visible
logical identity across lazy/eager and main/port. A mismatch aborts the run.
This is text/geometry verification, not a color/style comparison.

`main` is also a standalone correctness smoke: it runs both modes and checks
all 40 frames before printing the returned-to-top frame. The retained frame
visualization in `.amp/in/artifacts/complex-feed.png` was inspected at the top
and after 20 downward steps; header/footer, wrapped descriptions, gallery tiles
and viewport clipping are intact. It is not a live terminal screenshot.

## Individual-interaction baseline: September 12, 2026

Baseline: fetched `origin/main` at
[`650013d`](https://github.com/akonwi/cooper/commit/650013dc9525c504b42089cb5c30ddd54e3c5ff0).
Candidate: `ard-native-layout` at
[`b78727a`](https://github.com/akonwi/cooper/commit/b78727a840239b3e239b944dc748033eca78c178),
whose production layout is unchanged from the completed port checkpoint.
Both compile identical fixture and driver sources with the installed Ard compiler
(clean revision `3fd626729f1e5be16d6bd074dc5f900060861f63`, reporting `dev`) and
Go 1.27.0 in the same two-CPU Linux/amd64 orb, using default GC settings.
No concurrent benchmark/build/test jobs ran during measurement.

Thirty measured sessions plus three warmups per revision/mode; both revision
and mode order alternate. There are 1,200 measured interactions in each of the
four groups, 4,800 total. Including warmups, all **5,280 frame checks passed**.

Each sample times `Session.step`: window updates, retained creation/destruction,
scrolling and synchronous headless rendering. Memory-stat reads, validation,
hashing and setup/destruction are outside that interval. There is no forced GC
between steps. Validation still affects surrounding heap/cache state, so these
are instrumented headless interaction timings, not physical input-to-photon
latency or a terminal frame-rate guarantee.

| Mode / revision | Median scroll ms | p95 ms | p99 ms | Max ms | Median startup ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| Lazy / main | 2.740 | 4.020 | 5.301 | 8.429 | 5.320 |
| Lazy / Ard | 2.714 | 3.729 | 5.428 | 12.835 | 4.676 |
| Eager / main | 63.915 | 75.108 | 88.602 | 132.717 | 171.119 |
| Eager / Ard | 57.509 | 70.449 | 88.689 | 129.699 | 149.611 |

These percentiles are over individual scroll calls, unlike the earlier
profiling baseline's batch-average percentiles. Startup includes construction,
first render and the fixture's initial height checks, and is measured separately.

Median Go heap traffic per scroll:

| Mode / revision | Bytes | Allocations |
| --- | ---: | ---: |
| Lazy / main | 2,202,072 | 19,138 |
| Lazy / Ard | 2,278,840 | 19,925.5 |
| Eager / main | 54,440,608 | 892,844 |
| Eager / Ard | 54,440,632 | 892,849 |

Fractional median counts arise from averaging the two middle integer samples.
These figures exclude native Yoga allocations and are not live/peak memory.

**The port remains comparable on the intended lazy workload.** Eager mode is
dramatically slower on both engines, establishing that the fixture detects
the cost of retaining the whole feed. This does not isolate layout from paint
or establish the cause of every outlier. No production optimization was made.

## Reproduce and retain the evidence

Commands are in [benchmarks/README.md](../benchmarks/README.md#complex-feed-reference-workload).
The runner temporarily copies its fixture into the baseline checkout, restores
the generated Go entry file after building, and cleans up its copied source.
Do not run another Ard build in either checkout concurrently.

Raw samples, frame hashes, representative frame text, source hashes, revisions
and summaries are preserved as `complex-feed-2026-09-12.json.gz` in the
[Git archive](https://github.com/akonwi/cooper/tree/e100649ecb4f83740fbcceab13cd701f37d4fe43/benchmarks/baselines),
not the current checkout. The benchmark guide explains retrieval and where to
save new generated results.

Use this fixture before optimizing against an assumed complex-feed bottleneck;
preserve all frame checks and compare both timing distributions and allocation
traffic on the same machine.
