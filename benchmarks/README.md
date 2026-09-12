# Retained layout experiments

Run the benchmark suite from the repository root:

```sh
ARD=ard python3 benchmarks/run.py
```

The runner builds each benchmark once, performs three warmups, then reports the
median and p95 of 25 process-level samples. Runs with fewer than 20 samples label
the nearest-rank tail value as `max` instead.

## Workloads

- `retained_layout.ard`: 1,001 persistent retained nodes.
- `retained_virtual_list.ard`: 10,000 logical string rows represented by a
  reusable 64-row retained window, two spacers, content, and viewport (68
  retained nodes total).
- `retained_stress.ard`: 1,000 detach/re-attach/frame cycles plus 100-level
  clipped trees exercised through TestApp mouse routing and rendering.
- `retained_interaction.ard`: 100 fully overlapping z-index siblings under
  10,000 pointer moves plus 100 selections through 200 retained Text controls.

The same workloads compile against main's Tess backend and the Ard port.
Legacy `backend=tess_*` output labels identify workloads, not the active solver.

The virtual-list benchmark measures the supported TestApp surface: initial
render, a jump to row 5,000, one visible-row update, 100 one-row window shifts,
resize, and a forced clipped render.
It intentionally remains benchmark-local until another application confirms a
public virtualization API.

The stress benchmark reports total microseconds for 1,000
detach/re-attach/render cycles, 10,000 deep TestApp mouse events, and 1,000 deep
renders. It panics unless every routed event and the final painted cell reach the
leaf, so traversal work cannot be optimized away or silently terminate early.

The interaction benchmark reports stacking-aware hit traversal and global
selection reconciliation separately. It verifies that every pointer event
reaches the highest z-index sibling and that selection produces non-empty text.

## Main-branch baseline and profiling

See [the recorded baseline](../docs/layout-profiling-baseline.md) for revisions,
measurements, profile findings and limitations. No production instrumentation is
required. Use a separate checkout and run these commands sequentially, without
other benchmarks or builds competing for CPU:

```sh
git fetch origin
git worktree add --detach /tmp/cooper-profile-main origin/main
python3 benchmarks/profile.py /tmp/cooper-profile-main . \
  --samples 25 --operations 1000 --profile-seconds 5 \
  --output /tmp/cooper-profiles
python3 benchmarks/compare.py /tmp/cooper-profile-main . \
  --samples 25 --warmups 3 --output /tmp/cooper-retained.json
git worktree remove /tmp/cooper-profile-main
```

`profile.py` copies its Ard fixture into the baseline only if absent, removes
that copy afterward, and refuses to overwrite different source. It replaces
only generated `main.go` with a Go profiling driver while building each binary,
then restores that generated file. Do not run another Ard build in either
checkout concurrently. The generated Go directory is compiler-version-specific.

Four isolated workloads distinguish layout-only from full headless rendering,
each with unchanged content or an alternating single-row content update.
Layout uses 64 fixed-size Text rows; render uses a scrolled 64-row window in
10,000 logical rows. Setup, ten warmup operations, forced GC and correctness
checks are outside each timed batch. Three process warmups precede the measured
samples, whose branch order alternates. Reported p95 is the percentile of batch
averages, **not individual-frame p95**.

CPU and sampled allocation profiles run separately after all timing samples.
`results.json` records revisions, source hashes, raw samples, medians and p95.
`*.cpu`, `*.before`, `*.after` and text reports preserve CPU and allocation
evidence. Allocation deltas from `runtime.MemStats` measure Go heap traffic,
not peak/live memory or Yoga's C++ allocations. Sampled before/after profiles
also contain small profiling-writer allocations; exclude those when diagnosing
framework costs. CPU percentages include background GC and are not additive
when cumulative call stacks overlap.

## Complex feed reference workload

`complex_feed.ard` adapts the nested, variable-height feed and down/up scrolling
shape of Flutter's `complex_layout` benchmark. It is benchmark-only, not an
interactive application or a Flutter source port. See
[the workload and baseline](../docs/complex-feed-benchmark.md).

```sh
# Correctness smoke: compare lazy/eager after every step and print the final frame.
ard build benchmarks/complex_feed.ard --out /tmp/complex-feed
/tmp/complex-feed

# Benchmark identical code against fetched main, without concurrent builds/tests.
git fetch origin
git worktree add --detach /tmp/cooper-complex-main origin/main
python3 benchmarks/complex_feed.py /tmp/cooper-complex-main . \
  --samples 30 --output /tmp/complex-feed-results.json
git worktree remove /tmp/cooper-complex-main
```

This runner reports individual synchronous scroll-to-headless-frame latency,
not batch averages or PTY input-to-display latency. It compares every frame's
text and scroll/visible identity across both modes and revisions before accepting
the results. Like `profile.py`, it instruments only generated Go entry code and
restores it afterward. Its temporary baseline fixture is removed on completion.

The feed and pager comparators use `isolated-verification-v2`: each session runs
full per-frame correctness checks in a separate `-verify` process, then measures
the same sequence in a fresh process without intermediate frame serialization.
The measured process checks its final frame after the timing loop. Reports retain
verification records separately from timing samples and compare final hashes.
GC settings are unchanged. This prevents verification allocations from affecting
the next timed step's GC, but does not remove the workload's own allocation costs.
Compare revisions using the same runner; timings from the older interleaved
verification protocol are not directly comparable. Test the process contract with
`python3 benchmarks/test_measurement_protocol.py`.

## Three-way Bubble Tea pager comparison

`compare_bubbletea.py` compares main, the current Cooper branch and native Go
Bubble Tea/Bubbles using the same 10,000-line pager data and 80×24 viewport.
The shared driver checks every generated frame against independently clipped
source rows. This measures update/view computation, excluding terminal renderer
cadence, coalescing, diffing and I/O on all sides.

See [commands and pinned dependencies](bubbletea_pager/README.md) and
[the three-way results](../docs/bubbletea-pager-benchmark.md). Bubble Tea lives in
an isolated benchmark Go module; production dependencies are unchanged.
