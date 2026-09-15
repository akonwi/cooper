# CUI eager versus virtual-list benchmark

`benchmarks/cui_virtual_list.ard` compares eager and virtual rendering of the
same already-loaded integer data. Each row is a nested CUI box containing one,
two, or three deterministic text lines. The benchmark performs no network or
file I/O in the measured process.

## Method

The Python runner builds one release binary before measurement, then launches
an isolated process for each mode and size. `/usr/bin/time` records peak process
RSS, so compiler memory is excluded. Runs alternate eager/virtual order. The
headless viewport is 80 by 24 cells in every case.

Mount timing includes CUI mount and the first flush. The jump workload visits
six equivalent logical rows (offsets are exact under the 1/2/3-cell height
cycle), flushing and checking that every target was painted. The scroll workload
applies ten identical relative cell deltas with a flush after each. The final
frame must begin with row 37's detail line and contain row 38's expected label.
Build and mounted-row counters provide additional evidence of work performed.

Run it from the repository root:

```sh
ard format --check benchmarks/cui_virtual_list.ard
ard check benchmarks/cui_virtual_list.ard
python3 benchmarks/cui_virtual_list.py --samples 10 --warmups 2
```

## Results

Measured in the Amp Linux x86-64 orb on 2026-09-15 with Ard 0.42.0. Values are
median / p95 over 10 measured isolated processes after two warmups. Latencies
are microseconds and RSS is KiB.

| Items | Mode | mount+flush | 6 jumps | 10 scrolls | peak RSS | initial / total builds | mounted rows |
|---:|:---|---:|---:|---:|---:|---:|---:|
| 1,000 | eager | 111,598 / 127,450 | 13,802 / 21,073 | 21,712 / 25,460 | 59,222 / 62,960 | 1,000 / 1,000 | 1,000 |
| 1,000 | virtual | 3,320 / 4,027 | 25,288 / 31,812 | 19,884 / 21,290 | 9,590 / 9,864 | 55 / 992 | 21 |
| 4,000 | eager | 921,491 / 973,556 | 64,178 / 85,806 | 95,433 / 112,105 | 226,640 / 232,532 | 4,000 / 4,000 | 4,000 |
| 4,000 | virtual | 6,510 / 8,107 | 27,208 / 30,053 | 21,855 / 26,526 | 9,610 / 10,088 | 55 / 992 | 21 |

Both modes ended at cell offset 74 in every sample. Virtual `total_builds`
counts all materializations across jumps and scrolling, not unique rows.
Virtualization greatly reduces mount cost and resident memory here, but is not
uniformly faster: the 1,000-row jump workload favors the already-mounted eager
tree. At 4,000 rows both jump and scroll workloads favor virtualization.

## Limitations

These are end-to-end headless timings from one shared orb, not CPU-isolated
microbenchmarks. Peak RSS includes the Ard/Go runtime and allocator slack, and
`time` samples only whole-process high-water memory. The deterministic row
cycle makes target offsets equivalent and reproducible but does not represent
arbitrary prose wrapping. This measures already-loaded data only; loading,
networking, terminal startup, and interactive input are intentionally excluded.
