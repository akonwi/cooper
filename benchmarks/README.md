# Retained layout experiments

Run the benchmark comparison from the repository root:

```sh
ARD=ard-dev python3 benchmarks/run.py
```

The runner builds each benchmark once, performs three warmups, then reports the
median and p95 of 25 process-level samples. Runs with fewer than 20 samples label
the nearest-rank tail value as `max` instead.

## Compared shapes

- `retained_layout.ard`: 1,001 persistent Tess/Yoga-backed retained nodes.
- `surface_layout.ard`: the current Ard `Column` rendering 1,000 mutable child
  widgets into newly allocated `Surface` trees.
- `retained_virtual_list.ard`: 10,000 logical string rows represented by a
  reusable 64-row retained window, two spacers, content, and viewport (68
  retained nodes total).
- `retained_stress.ard`: 1,000 detach/re-attach/layout cycles plus 100-level
  clipped trees exercised by repeated hit tests and direct paints.

The Tess and Ard Surface numbers are directional, not an isolated layout-engine
shootout. The Surface path includes fresh Surface/list allocation on every
render, while the retained path mutates an attached layout tree. This is the
architecture-level comparison Cooper currently needs; an Ard-native Yoga port
should later use identical retained-node workloads for a backend-only
comparison.

The virtual-list benchmark measures initial layout, a jump to row 5,000, one
visible-row update, 100 one-row window shifts, resize, and direct clipped paint.
It intentionally remains benchmark-local until another application confirms a
public virtualization API.

The stress benchmark reports total microseconds for 1,000
detach/re-attach/layout cycles, 10,000 deep hit tests, and 1,000 deep paints.
It panics unless every hit and the final painted cell reach the leaf, so traversal
work cannot be optimized away or silently terminate early.
