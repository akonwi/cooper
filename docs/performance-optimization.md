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

## Skip clipped Text content and reuse per-paint layout

Checkpoint [8502d3b](https://github.com/akonwi/cooper/commit/8502d3b2872c01b03941e5dc7191255f521de79c)
compared with [27ab359](https://github.com/akonwi/cooper/commit/27ab35923036daa8f2edf12b7f3f0ac1f00be754).
Text skips content layout and painting when its content clip has zero width or
height, after painting borders and clearing stale link-hit data. It preserves
logical selection. No Node traversal or arbitrary user paint callback is skipped.
Visible linked/styled/ellipsized Text passes its already-computed layout into
visual mapping; no persistent cache or width-measurer replacement was added.

Standard measurements (30 pager and 15 feed sessions, each plus three warmups):

| Median | Reference | Candidate |
|---|---:|---:|
| Pager down | 0.493 ms | 0.472 ms |
| Lazy feed | 1.116 ms | 1.286 ms |
| Eager feed | 38.169 ms | 2.698 ms |
| Lazy allocated bytes/step | 1,103,432 | 834,856 |
| Eager allocated bytes/step | 23,578,264 | 1,030,208 |

Eager median improved about 93%, but the standard lazy median worsened about
15%. Lazy p95 was essentially unchanged (1.781 vs 1.755 ms). Bubble Tea pager
median was 0.173 ms; this work does not materially close that gap. All 26,640
standard benchmark frame checks passed.

### Inter-step verification affects GC timing

Investigation found `Frame.text()` constructs its output by repeatedly
concatenating a growing prefix. The feed's serialization/verification allocates
about **7.2 MB after every step**, outside the timer but in the same process.
Excluding that code from timing does not exclude its influence on garbage
collection during the next measured step.

A separate diagnostic used the same lazy workload and default GC settings,
alternating revisions and verification modes across ten samples plus three
warmups. It verifies either between every step, or only before and after the
40-step timed sequence:

| Diagnostic median | Reference | Candidate |
|---|---:|---:|
| Verification between steps | 1.097 ms | 1.226 ms |
| Verification only at start/end | 1.160 ms | 0.681 ms |

This demonstrates sensitivity to verification placement; it does not replace
the standard results or prove performance under every application workload.
The start/end mode alone does not validate intermediate frames. Their correctness
was established by the separate standard run. No GC tuning, benchmark-specific
production branch, or change to the existing benchmark runner was introduced.

Verification: **437 Ard tests passed**, no failures/panics; format/check passed;
Go tests passed. Nine affected PTY examples passed: text gallery, layout
playground, links, Input, TextArea, Select, scroll form, horizontal scroll, and
interaction. Tinear check/build and smoke passed, with its same previously
established 149-pass/one-divider-failure unit result. Focused tests assert zero
clipped-text measurements, stale-link cleanup, border/selection restoration,
and three rather than four first-glyph measurements for linked, styled, and
ellipsized paints. Existing tests cover visible overflow and partial wide glyphs.

Raw evidence: `performance-visible-pager.json.gz`,
`performance-visible-feed.json.gz`, and `performance-visible-gc-diagnostic.json.gz`
under `benchmarks/baselines`. Diagnostic source:
`benchmarks/complex_feed_gc_diagnostic.go.template`. To reproduce, first build
`benchmarks/complex_feed.ard` in each checkout. Copy the diagnostic template to a
temporary `.go` file and run `go build -o /tmp/feed-diagnostic /tmp/diagnostic.go`
from that checkout's `ard-out/go/build` directory. Run the resulting binary with
`-verify-each=true` and `-verify-each=false`, separately and without competing work.

Before using small lazy-feed timing differences to accept or reject future
optimizations, address the verification-allocation interference explicitly.

## Isolated verification establishes the next comparison baseline

Checkpoint [a03541b](https://github.com/akonwi/cooper/commit/a03541b5abfc584723e326b1787a9f3d421fe7be)
separates full frame verification from measurement into different processes.
Each measured sequence checks its final frame only after its timing loop; a
separate process checks every intermediate frame. Both comparators reject
sequence or final-frame mismatches and store verification records separately.
No GC settings, workloads, or production rendering paths changed in this
checkpoint. `Frame.text()` now joins grapheme parts once instead of repeatedly
copying a growing prefix; it preserves the serialized output.

The same new harness ran against reference
[27ab359](https://github.com/akonwi/cooper/commit/27ab35923036daa8f2edf12b7f3f0ac1f00be754)
and this checkpoint, using 30 pager sessions and 15 feed sessions, each plus three
warmups, on the same two-CPU orb with Go 1.27.0 and Ard compiler revision
`3fd626729f1e5be16d6bd074dc5f900060861f63`. Reference means the pre-clipped-Text
optimization checkpoint, **not current main** (the pager JSON calls it `main`).

| Per-step latency | Reference median / p95 | Candidate median / p95 | Bubble Tea median / p95 |
|---|---:|---:|---:|
| Pager down | 0.325 / 0.937 ms | 0.315 / 0.926 ms | 0.169 / 0.246 ms |
| Lazy feed | 1.157 / 2.069 ms | 0.680 / 1.566 ms | — |
| Eager feed | 37.984 / 46.462 ms | 2.745 / 3.697 ms | — |

Lazy median is about 41% lower and eager about 93% lower under this protocol.
Pager's roughly 3% median difference is small; Cooper remains about 1.86× Bubble
Tea's median and 3.76× its p95. Median pager-down heap traffic remains
308,088 bytes against Bubble Tea's 34,464 bytes. Lazy/eager candidate heap traffic
is 834,868 / 1,030,208 bytes per step, against 1,103,448 / 23,578,264 bytes in the
reference. These are Go allocations, not retained memory.

This comparison evaluates the earlier clipped-Text/layout-reuse optimization
with consistent measurement isolation. The lower absolute pager timings than
the old report are **not a newly achieved library speedup**. Old interleaved
results remain historical evidence, not a directly comparable baseline. Small
differences still need repeated measurements; process isolation removes this
specific verification/GC interaction, not all measurement noise.

Proof: `ard test` reported **438 passed; 0 failed; 0 panicked**. Ard format/check
passed. `python3 benchmarks/test_measurement_protocol.py` passed two black-box
tests: measured adapters reject early serialization and verification catches
injected intermediate failures. Root and native pager `go test ./...` passed.
All **26,640** per-frame checks across benchmark sessions and warmups passed,
and all measured final hashes matched the verified sequences. No appearance or
interactive production behavior changed in this checkpoint.

Raw records: `benchmarks/baselines/performance-isolated-pager.json.gz` and
`benchmarks/baselines/performance-isolated-feed.json.gz`, tagged
`isolated-verification-v2`. Reproduce with the current runners and a detached
reference worktree:

```sh
git worktree add --detach /tmp/cooper-isolated-reference 27ab35923036daa8f2edf12b7f3f0ac1f00be754
python3 benchmarks/compare_bubbletea.py /tmp/cooper-isolated-reference . --samples 30 --output /tmp/cooper-isolated-pager.json
python3 benchmarks/complex_feed.py /tmp/cooper-isolated-reference . --samples 15 --output /tmp/cooper-isolated-feed.json
git worktree remove /tmp/cooper-isolated-reference
```
