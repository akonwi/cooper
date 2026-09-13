# Three-way pager benchmark — September 12, 2026

## Reference and scope

The [official Bubble Tea pager example](https://github.com/charmbracelet/bubbletea/blob/v2.0.9/examples/pager/main.go)
delegates message handling and view generation to Bubbles' viewport. This
benchmark follows that pattern, omitting the example's decorative header/footer
and interactive terminal program. Bubble Tea's upstream
[`BenchmarkTeaRun`](https://github.com/charmbracelet/bubbletea/blob/v2.0.9/tea_test.go)
instead exercises program lifecycle with input pipes and sleeps; it is not a
comparable update/view throughput workload.

Compared implementations:

- Cooper fetched `origin/main` at
  [`650013d`](https://github.com/akonwi/cooper/commit/650013dc9525c504b42089cb5c30ddd54e3c5ff0), using Tess/Yoga.
- Cooper `ard-native-layout` at
  [`87299f8`](https://github.com/akonwi/cooper/commit/87299f8b78480118e7608e5756d2444a66fbc066).
- Native Go, pinned `charm.land/bubbletea/v2 v2.0.9` and
  `charm.land/bubbles/v2 v2.2.1`, with transitive versions recorded in the nested
  benchmark module's `go.mod` and `go.sum`. Both libraries are MIT licensed.

All run on the same two-CPU Linux/amd64 orb, Go 1.27.0, default GC settings.
Both Cooper variants use the same installed Ard compiler (reports `dev`, clean
[revision 3fd6267](https://github.com/akonwi/ard/commit/3fd626729f1e5be16d6bd074dc5f900060861f63)).
Production code is unchanged. The Bubble Tea dependencies exist only in
`benchmarks/bubbletea_pager`, not Cooper's root or examples modules.

## Identical behavior, idiomatic implementation strategies

The shared Go driver creates 10,000 ASCII lines with numbered prefixes and
14 varying lengths spanning both sides of the 80-column clipping boundary.
The viewport is 80×24, unwrapped. Each session performs 100 one-line downward
scrolls, 100 upward scrolls returning to zero, then 40 unchanged renders.

Bubble Tea receives `j`/`k` key messages through `viewport.Update`, followed by
`viewport.View` every time. Cooper maps the same semantic scroll commands into
an app-local 24-row window, updating persistent Text nodes before a full
headless render. Both retain the complete source corpus. Bubble Tea preprocesses
the corpus in `SetContentLines`; Cooper initializes only the visible Text nodes.
Startup numbers must be read with that difference in mind.

The measured interval is update plus view generation. Bubble Tea produces its
view string; Cooper produces its cell buffer. Cooper frame-to-text conversion,
normalization, validation and hashing occur afterward, outside the timing and
allocation interval. This does not charge Cooper for serialization that it
does not need for its normal cell-based renderer.

The common independent oracle clips/pads the expected 24 source rows. Every
actual frame must equal it. Normalization only supplies trailing spaces or
removes one terminal newline; it does not strip ANSI or hide content differences.
Frame hashes also must agree across all three implementations.

Thirty measured sessions and three warmups per implementation, with run order
rotating each iteration. All **23,760 step-frame checks** passed, including
warmups; raw measurements contain 21,600 steps. Startup is timed separately.
Per-step memory-stat reads and assertions are outside the interval, but can
affect surrounding cache/heap state. No forced GC occurs between events.

## Bubble Tea is faster for this pager; the two Cooper branches remain close

Individual event latency, in microseconds. Percentiles are over events, not
batch averages. No competing builds or benchmark jobs ran during measurement.

| Event | Implementation | Median µs | p95 µs | p99 µs |
| --- | --- | ---: | ---: | ---: |
| Down | Cooper main | 1,124.79 | 1,698.77 | 2,141.15 |
| Down | Cooper Ard | 1,142.76 | 1,732.56 | 2,139.74 |
| Down | Bubble Tea/Bubbles | 149.79 | 271.60 | 489.44 |
| Up | Cooper main | 1,123.77 | 1,662.37 | 2,006.37 |
| Up | Cooper Ard | 1,123.85 | 1,705.37 | 2,164.53 |
| Up | Bubble Tea/Bubbles | 145.55 | 207.84 | 382.18 |
| Unchanged | Cooper main | 1,091.22 | 1,567.88 | 1,958.98 |
| Unchanged | Cooper Ard | 1,095.73 | 1,671.37 | 2,040.94 |
| Unchanged | Bubble Tea/Bubbles | 144.01 | 229.96 | 399.40 |

Median startup: main **2.159 ms**, Ard **2.335 ms**, Bubble Tea **11.550 ms**.
This includes model/content preparation and the first generated view, but not
shared fixture-string generation or a terminal's startup handshake.

Median Go allocation traffic per downward scroll:

| Implementation | Bytes | Allocations |
| --- | ---: | ---: |
| Cooper main | 808,416 | 6,481 |
| Cooper Ard | 826,976 | 6,623 |
| Bubble Tea/Bubbles | 34,464 | 1,678 |

The native pager's downward-scroll median is about 7.5× lower than main and
7.6× lower than the Ard branch. This gap is already present on main: it is not
evidence that porting Tess to Ard caused a comparable slowdown. The fixture
contrasts a specialized viewport's string processing with Cooper's retained
Text/layout/paint pipeline, including their different preparation strategies.
It does not isolate language overhead or predict results for a complex app.

## What this intentionally does not measure

- No `tea.Program` or terminal renderer is started. Bubble Tea's default 60 FPS
  flushing, configurable cap, view coalescing, terminal diffing and writes are
  absent. We do not use `WithoutRenderer`, which would not be equivalent to
  explicitly generating every view.
- Cooper does not present its frame through Vaxis. Its normal terminal diffing,
  writes, keyboard parsing and event routing are likewise absent.
- No physical input-to-display latency, terminal bytes written, dropped frames,
  complex layout, Unicode shaping, style changes, resizing or popup behavior.
- Go heap traffic excludes Yoga's native allocations and is not peak/live
  memory. Absolute timings are orb-specific, not universal performance gates.

This answers a narrow but useful question: how expensive is generating the same
simple scrolling text viewport through these three implementations? It is not
a claim that all Bubble Tea applications run 7.6× faster than Cooper.

## Reproduce and inspect

See [the native benchmark README](../benchmarks/bubbletea_pager/README.md) for
commands. `compare_bubbletea.py` builds separate binaries with the same Go driver,
checks every frame and rotates their execution order. No production dependency
or backend switch is added.

Raw samples, representative frame text, dependency list, source hashes and
summaries are preserved as `bubbletea-pager-2026-09-12.json.gz` in the
[Git archive](https://github.com/akonwi/cooper/tree/e100649ecb4f83740fbcceab13cd701f37d4fe43/benchmarks/baselines),
not the current checkout. See the [benchmark guide](../benchmarks/README.md)
for retrieval and where to save new generated results.
