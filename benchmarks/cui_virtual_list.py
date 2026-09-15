#!/usr/bin/env python3
"""Build once, then benchmark eager and virtual CUI lists in isolated processes."""

from __future__ import annotations

import argparse
import os
import statistics
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "benchmarks/cui_virtual_list.ard"


def parse(stdout: str) -> dict[str, int | str]:
    fields: dict[str, int | str] = {}
    for field in stdout.strip().split():
        key, value = field.split("=", 1)
        fields[key] = int(value) if value.lstrip("-").isdigit() else value
    required = {"mount_us", "jump_us", "scroll_us", "initial_builds", "total_builds", "mounted_rows", "final_top"}
    if not required <= fields.keys():
        raise RuntimeError(f"incomplete benchmark output: {stdout!r}")
    return fields


def percentile(values: list[int], percent: int) -> int:
    ordered = sorted(values)
    return ordered[(len(ordered) * percent + 99) // 100 - 1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=10)
    parser.add_argument("--warmups", type=int, default=2)
    args = parser.parse_args()
    if args.samples < 1 or args.warmups < 0:
        parser.error("samples must be positive and warmups non-negative")

    with tempfile.TemporaryDirectory(prefix="cooper-cui-list-") as directory:
        binary = Path(directory) / "benchmark"
        subprocess.run(["ard", "build", "--release", str(SOURCE), "--out", str(binary)], cwd=ROOT, check=True)
        results: dict[tuple[int, str], list[dict[str, int | str]]] = {}
        for iteration in range(args.warmups + args.samples):
            for count in (1000, 4000):
                modes = ("eager", "virtual") if iteration % 2 == 0 else ("virtual", "eager")
                for mode in modes:
                    env = os.environ | {"COOPER_BENCH_MODE": mode, "COOPER_BENCH_COUNT": str(count)}
                    completed = subprocess.run(
                        ["/usr/bin/time", "-f", "%M", str(binary)], cwd=ROOT, env=env,
                        text=True, capture_output=True, check=True,
                    )
                    sample = parse(completed.stdout)
                    sample["peak_rss_kib"] = int(completed.stderr.strip().splitlines()[-1])
                    if iteration >= args.warmups:
                        results.setdefault((count, mode), []).append(sample)

    print(f"samples={args.samples} warmups={args.warmups} (median, p95; RSS is process max KiB)")
    metrics = ("mount_us", "jump_us", "scroll_us", "peak_rss_kib", "initial_builds", "total_builds", "mounted_rows")
    for count in (1000, 4000):
        for mode in ("eager", "virtual"):
            samples = results[count, mode]
            summary = []
            for metric in metrics:
                values = [int(sample[metric]) for sample in samples]
                summary.append(f"{metric}={round(statistics.median(values))}/{percentile(values, 95)}")
            tops = {int(sample["final_top"]) for sample in samples}
            if len(tops) != 1:
                raise RuntimeError(f"non-deterministic final offset: {count}/{mode}: {tops}")
            print(f"count={count} mode={mode} " + " ".join(summary) + f" final_top={tops.pop()}")


if __name__ == "__main__":
    main()
