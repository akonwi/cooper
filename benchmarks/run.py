#!/usr/bin/env python3
"""Build and summarize Cooper's retained-layout experiments."""

from __future__ import annotations

import argparse
import os
import shlex
import statistics
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARD = shlex.split(os.environ.get("ARD", "ard-dev"))
BENCHMARKS = {
    "tess_retained": ROOT / "benchmarks" / "retained_layout.ard",
    "ard_surface": ROOT / "benchmarks" / "surface_layout.ard",
    "tess_virtual": ROOT / "benchmarks" / "retained_virtual_list.ard",
    "tess_stress": ROOT / "benchmarks" / "retained_stress.ard",
}


def parse_metrics(output: str) -> dict[str, int | str]:
    line = next((line for line in reversed(output.splitlines()) if "=" in line), "")
    metrics: dict[str, int | str] = {}
    for field in line.split():
        if "=" not in field:
            continue
        key, value = field.split("=", 1)
        try:
            metrics[key] = int(value)
        except ValueError:
            metrics[key] = value
    if not metrics:
        raise RuntimeError(f"benchmark produced no metrics:\n{output}")
    return metrics


def percentile_95(values: list[int]) -> int:
    ordered = sorted(values)
    return ordered[max(0, (len(ordered) * 95 + 99) // 100 - 1)]


def summarize(samples: list[dict[str, int | str]]) -> dict[str, int | str]:
    result: dict[str, int | str] = {}
    for key in samples[0]:
        values = [sample[key] for sample in samples]
        if all(isinstance(value, int) for value in values):
            numeric = [int(value) for value in values]
            result[key] = round(statistics.median(numeric))
            result[f"{key}_p95"] = percentile_95(numeric)
        else:
            result[key] = values[-1]
    return result


def run_binary(binary: Path, count: int, warmups: int) -> dict[str, int | str]:
    for _ in range(warmups):
        subprocess.run([str(binary)], cwd=ROOT, check=True, capture_output=True, text=True)
    samples = []
    for _ in range(count):
        completed = subprocess.run(
            [str(binary)], cwd=ROOT, check=True, capture_output=True, text=True
        )
        samples.append(parse_metrics(completed.stdout))
    return summarize(samples)


def build(source: Path, output: Path) -> None:
    subprocess.run(
        [*ARD, "build", "--out", str(output), str(source)],
        cwd=ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )


def print_summary(
    results: dict[str, dict[str, int | str]], sample_count: int
) -> None:
    tail_label = "p95" if sample_count >= 20 else "max"
    print(f"Median µs ({tail_label} in parentheses; lower is better)")
    print("metric                 tess retained      Ard Surface       surface/tess")
    for metric in ("construct_us", "initial_layout_us", "single_update_us", "resize_us"):
        tess = int(results["tess_retained"][metric])
        tess_p95 = int(results["tess_retained"][f"{metric}_p95"])
        surface = int(results["ard_surface"][metric])
        surface_p95 = int(results["ard_surface"][f"{metric}_p95"])
        ratio = surface / tess if tess else float("inf")
        print(
            f"{metric:<22} {tess:>6} ({tess_p95:>6})"
            f" {surface:>10} ({surface_p95:>6}) {ratio:>12.2f}x"
        )

    virtual = results["tess_virtual"]
    print("\n10,000 logical rows / 68 retained nodes")
    for metric in (
        "logical_construct_us",
        "retained_construct_us",
        "initial_layout_us",
        "jump_layout_us",
        "single_row_update_us",
        "window_shift_avg_us",
        "resize_us",
        "paint_us",
    ):
        print(
            f"{metric:<24} {int(virtual[metric]):>6}"
            f" ({int(virtual[f'{metric}_p95']):>6})"
        )

    stress = results["tess_stress"]
    print("\nRetained mutation and depth stress")
    for metric in (
        "attach_detach_layout_1000_us",
        "deep_layout_us",
        "deep_hit_10000_us",
        "deep_paint_1000_us",
    ):
        print(
            f"{metric:<24} {int(stress[metric]):>6}"
            f" ({int(stress[f'{metric}_p95']):>6})"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=25)
    parser.add_argument("--warmups", type=int, default=3)
    args = parser.parse_args()
    if args.iterations < 1 or args.warmups < 0:
        parser.error("iterations must be positive and warmups non-negative")

    with tempfile.TemporaryDirectory(prefix="cooper-bench-") as directory:
        output_dir = Path(directory)
        binaries = {}
        for name, source in BENCHMARKS.items():
            binary = output_dir / name
            build(source, binary)
            binaries[name] = binary

        results = {
            name: run_binary(binary, args.iterations, args.warmups)
            for name, binary in binaries.items()
        }
    print_summary(results, args.iterations)


if __name__ == "__main__":
    main()
