# Performance optimization checkpoints

## Streaming text and conditional layout snapshots

The first checkpoint on `bubbletea-performance` is
[`9861005`](https://github.com/akonwi/cooper/commit/9861005b58eaf98878a10b9f9d221b6e5d501fca).
Its reference is the accepted Tess-removal checkpoint
[`be80065`](https://github.com/akonwi/cooper/commit/be800651ff4a675f524dddbe3aae28d179ef1976),
not the Tess-backed main branch. The historical main comparison remains in
[the original pager report](bubbletea-pager-benchmark.md).

The constraints remain: preserve the public API and functionality, support the
examples and Tinear, and make general library improvements rather than benchmark
special cases. No workload or benchmark adapter changed.

Changes:

- Check whether projected widths require replay before allocating horizontal and
  cache snapshots. When replay is needed, the same frozen geometry and restored
  natural-cache behavior apply.
- Use the already-pinned Vaxis character iterator for default headless width
  measurement, measured cell painting, and unwrapped Text layout. This avoids
  materializing intermediate character lists without changing segmentation.
- Assemble unwrapped lines once from grapheme parts rather than repeatedly
  concatenating their growing prefixes.

An attempted source-slicing variant was discarded: Vaxis expands tabs to eight
spaces, invalidating source offsets. The existing tab-selection regression caught
it. The committed implementation preserves Vaxis expansion and custom width
callbacks, without a measurement cache or buffer reuse.

## Results on the same two-CPU orb

Go 1.27.0, the same Ard compiler as the original baseline, default GC settings.
Jobs ran sequentially without competing test/build workloads. These are headless
computation measurements, not terminal input-to-display latency.

Pager: 30 measured sessions plus three warmups, rotating implementation order.
All 23,760 frame comparisons passed, including warmups.

| Pager down update | Accepted port | Optimized | Bubble Tea |
|---|---:|---:|---:|
| Median | 1.118 ms | 0.849 ms | 0.148 ms |
| p95 | 1.599 ms | 1.464 ms | 0.267 ms |
| Allocated bytes, median | 826,976 | 586,336 | 34,464 |
| Allocation count, median | 6,623 | 516 | 1,678 |

Median time improved 24%, allocated bytes 29%, and allocation count 92%.
Cooper is still about 5.7× slower than Bubble Tea here. Fewer allocation events
do not imply fewer allocated bytes or less GC work.

Complex feed: seven measured sessions plus three warmups; all 1,600 frame
comparisons passed across lazy/eager modes and both revisions.

| Feed scroll | Accepted port median / p95 | Optimized median / p95 |
|---|---:|---:|
| Lazy | 2.611 / 3.489 ms | 1.961 / 2.706 ms |
| Eager | 53.374 / 61.647 ms | 38.474 / 45.866 ms |

The focused profiler used seven samples of 300 operations and two-second CPU
profiles. Dirty-layout median fell from 36.8 to 32.8 µs; bytes/op fell from 40,749
to 27,020. Render timings had overlapping distributions; the pager/feed results
provide the stronger end-to-end evidence. In the unchanged-render allocation
profile, `paint::new_buffer` accounts for about 94% of sampled allocation space.

## Compatibility evidence and remaining work

- `ard test`: **431 passed, 0 failed, 0 panicked**.
- Formatting, format checks, and compiler checks passed for all five changed Ard
  files; `go test ./...` passed.
- All 20 PTY example scripts listed in `AGENTS.md` passed.
- Tinear at [389b939](https://github.com/akonwi/tinear/commit/389b939604c94964f7a0c1387f6f45e6527d3d19), with only disposable
  dependency metadata changed: check/build, Go tests, and startup/input/mouse/
  paste/clipboard/quit PTY smoke passed. Its Ard suite reports 149 passed and one
  failure, `inbox_loads_rows_and_discards_stale_detail_completion`:
  “Inbox panes should use a dim divider.” The same failure occurs against the
  accepted port checkpoint. This is not a fully green Tinear suite and is not
  attributed to these optimizations.

Next investigate cell-buffer allocation and representation. Previously returned
headless Frames must remain immutable snapshots; blindly reusing their storage
would be a correctness regression. The pinned Ard List API has no capacity or
length constructor. Do not add Go-owned framework behavior just to sidestep that
limitation. Benchmark any representation change against both pager and complex
feed, with clipping, overlapping wide cells, colors, hyperlinks, selection,
resize, and old-frame lifetime tests.

## Reproduction and raw evidence

From this checkpoint, create a detached worktree at the reference above, then:

```sh
python3 benchmarks/compare_bubbletea.py /tmp/cooper-perf-reference . \
  --samples 30 --output /tmp/pager.json
python3 benchmarks/complex_feed.py /tmp/cooper-perf-reference . \
  --samples 7 --output /tmp/feed.json
python3 benchmarks/profile.py /tmp/cooper-perf-reference . \
  --samples 7 --operations 300 --profile-seconds 2 --output /tmp/profile
```

Versioned raw results are `benchmarks/baselines/performance-streaming-pager.json`,
`performance-streaming-feed.json`, and `performance-streaming-profile.json`.
The pager runner calls its reference `main` and candidate `ard`; in this run
those mean **accepted port** and **optimized port**, respectively. Consult the
embedded revision fields rather than interpreting those labels as Git branches.

## Compact frame cells

The next checkpoint is
[`5ccf34c`](https://github.com/akonwi/cooper/commit/5ccf34cefd148d5474eec9f4197a396c89013b44),
compared with the preceding streaming implementation at
[`a047d01`](https://github.com/akonwi/cooper/commit/a047d01).

Internal stored cells now share a style snapshot per paint call instead of
embedding the full style in each cell. Blank cells share one immutable default
style. Public `paint::Cell` reads and testing Frames still return value styles;
the representation change is confined to the unsupported `core/paint` storage
and its terminal presenter. No new Go boundary or dependency was added.

Every rendered frame still owns fresh cell storage: this is not buffer pooling.
Styles are copied at the painting boundary and never mutated internally after
publication. Single-cell overwrite skips an unnecessary clear-before-write;
wide-span cleanup and cursor invalidation remain intact.

Same toolchain, fixtures, sequential measurement, and sample counts as above:

| Pager down update | Streaming checkpoint | Compact cells | Bubble Tea |
|---|---:|---:|---:|
| Median | 0.856 ms | 0.420 ms | 0.149 ms |
| p95 | 1.481 ms | 0.927 ms | 0.260 ms |
| Allocated bytes, median | 586,336 | 311,584 | 34,464 |
| Allocation count, median | 516 | 542 | 1,678 |

Median update time improved 51% and bytes 47% over the streaming checkpoint.
Allocation count increased slightly because style snapshots now have their own
allocation; the reduction in cell-array size more than offsets their bytes.
Cooper remains about 2.8× slower than Bubble Tea, with higher tail latency and
allocated bytes. Performance parity is not claimed.

| Feed scroll | Streaming median / p95 | Compact median / p95 |
|---|---:|---:|
| Lazy | 2.009 / 2.695 ms | 1.079 / 1.727 ms |
| Eager | 38.203 / 43.820 ms | 38.272 / 44.603 ms |

Eager feed performance is effectively unchanged; this optimization is not a
general layout speedup. All 23,760 pager and 1,600 feed frame comparisons passed.
The focused unchanged-render profile improved from 344 to 159 µs median and
495,907 to 224,226 bytes/op. Buffer construction still accounts for about 85% of
sampled allocation space; text layout/width measurement is also a significant
CPU cost. These remain the next profiling targets.

Verification: **433 Ard tests passed**, with zero failures/panics; all four
changed Ard files passed formatting and compiler checks; Go tests and all 20
example PTY scripts passed. New tests check caller/returned-cell style isolation,
shared wide-span hyperlinks, single-cell and overlapping-wide-cell cursor
invalidation, clear/repaint, and old Frames after redraw, resize, and destruction.
Tinear's check/build, Go tests, and PTY smoke passed again, with the same existing
149-pass/one-divider-failure Ard result documented above.

Raw results: `benchmarks/baselines/performance-compact-pager.json`,
`performance-compact-feed.json`, and `performance-compact-profile.json`.
Use the reproduction commands above with a detached reference at the streaming
checkpoint. In this pager report the runner's `main` label means **streaming
checkpoint**, not the repository's main branch.

## ASCII hard-break detection; source slicing rejected

Retained checkpoint:
[`ea32939`](https://github.com/akonwi/cooper/commit/ea3293967d24de9d91b761cf7794f1db34a2ef70),
compared with compact cells at
[`4ed92a3`](https://github.com/akonwi/cooper/commit/4ed92a353e52bcf77742d6742c71b91e8a6bc64d).
Newline detection now handles one-byte input directly; multibyte input keeps the
existing Unicode classification. Custom width callbacks and line allocation
remain unchanged.

| Workload median | Compact checkpoint | ASCII fast path |
|---|---:|---:|
| Pager down | 0.443 ms | 0.432 ms |
| Lazy feed | 1.101 ms | 1.060 ms |
| Eager feed | 39.320 ms | 37.638 ms |

This is a modest 2–4% median improvement, not a major reduction in the gap.
Allocated bytes are unchanged; tail distributions overlap. Pager p95 was
0.933 vs 0.940 ms. Bubble Tea measured 0.157 ms median in the same run, leaving
Cooper about 2.7× slower. Pager used 30 measured sessions plus three warmups;
feed used 15 plus three. All 26,640 frame checks passed.

Before this change, an allocation experiment at
[`ec39785`](https://github.com/akonwi/cooper/commit/ec397858e79af388598420d2ec9971e0dab402e7)
sliced unwrapped lines from tab-expanded source strings while measuring the
original Vaxis stream. It passed correctness tests and improved pager/eager-feed
results, but was **reverted** because lazy-feed performance regressed repeatedly.
In a 15-session repeat, lazy median increased from 1.202 to 1.509 ms despite
allocated bytes dropping from 1,103,432 to 869,368 per step. GC occurred during
571/600 candidate steps versus 223/600 reference steps; no-GC medians were close
(1.070 vs 1.092 ms). These are observations, not proof of a particular GC-pacer
mechanism. Copying completed lines rather than retaining source slices did not
remove the regression either. GC settings and benchmark boundaries were not
changed to accommodate the optimization.

Verification of the retained implementation: **435 tests passed, zero failures
or panics**; formatting/compiler checks passed. The text gallery, layout
playground, links, Input, TextArea, Select, and scroll-form PTY scripts passed.
Tinear check/build and PTY smoke passed; its unit suite still has the same
149-pass/one-divider-failure result. New tests cover ASCII and Unicode hard
breaks and deliberately non-additive custom measurement beside tabs, combining
marks, CRLF, and multibyte text.

Compressed raw evidence in `benchmarks/baselines/`:
`performance-ascii-pager.json.gz`, `performance-ascii-feed.json.gz`, and
`performance-rejected-slices-feed.json.gz`. Read with `gzip -dc`. The same
benchmark commands apply, using the compact checkpoint as reference and 15 feed
sessions. Do not treat the intermediate slicing commit as an accepted checkpoint.
