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
- `retained_stress.ard`: 1,000 detach/re-attach/frame cycles plus 100-level
  clipped trees exercised through TestApp mouse routing and rendering.
- `retained_interaction.ard`: 100 fully overlapping z-index siblings under
  10,000 pointer moves plus 100 selections through 200 retained Text controls.

A future Ard-native Yoga backend should use these same retained workloads for a
backend-only comparison.

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
