# Retained layout experiments

Run the benchmark suite from the repository root:

```sh
ARD=ard-dev python3 benchmarks/run.py
```

The runner builds each benchmark once, performs three warmups, then reports the
median and p95 of 25 process-level samples. Runs with fewer than 20 samples label
the nearest-rank tail value as `max` instead.

## Workloads

- `retained_layout.ard`: 1,001 persistent Tess/Yoga-backed retained nodes.
- `retained_virtual_list.ard`: 10,000 logical string rows represented by a
  reusable 64-row retained window, two spacers, content, and viewport (68
  retained nodes total).
- `retained_stress.ard`: 1,000 detach/re-attach/layout cycles plus 100-level
  clipped trees exercised by repeated hit tests and direct paints.

The superseded Surface implementation was removed after the architecture-level
comparison established the retained direction. A future Ard-native Yoga backend
should use these same retained workloads for a backend-only comparison.

The virtual-list benchmark measures initial layout, a jump to row 5,000, one
visible-row update, 100 one-row window shifts, resize, and direct clipped paint.
It intentionally remains benchmark-local until another application confirms a
public virtualization API.

The stress benchmark reports total microseconds for 1,000
detach/re-attach/layout cycles, 10,000 deep hit tests, and 1,000 deep paints.
It panics unless every hit and the final painted cell reach the leaf, so traversal
work cannot be optimized away or silently terminate early.
