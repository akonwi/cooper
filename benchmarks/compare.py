#!/usr/bin/env python3
"""Compare identical benchmark sources in two checkouts using alternating runs."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import statistics
import subprocess
import tempfile

from run import BENCHMARKS, parse_metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--samples", type=int, default=9)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.samples < 1 or args.warmups < 0:
        parser.error("samples must be positive and warmups non-negative")
    roots = {"baseline": args.baseline.resolve(), "candidate": args.candidate.resolve()}
    ard = shlex.split(os.environ.get("ARD", "ard"))
    report = {
        "compiler": subprocess.check_output([*ard, "version"], text=True).strip(),
        "go": subprocess.check_output(["go", "version"], text=True).strip(),
        "revisions": {
            name: subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
            for name, root in roots.items()
        },
        "tracked_diff_sha256": {
            name: hashlib.sha256(subprocess.check_output(["git", "diff", "HEAD"], cwd=root)).hexdigest()
            for name, root in roots.items()
        },
        "samples": args.samples,
        "warmups": args.warmups,
        "workloads": {},
    }
    with tempfile.TemporaryDirectory(prefix="cooper-compare-") as directory:
        for source in BENCHMARKS.values():
            relative = Path("benchmarks") / source.name
            contents = [(root / relative).read_bytes() for root in roots.values()]
            if contents[0] != contents[1]:
                raise RuntimeError(f"Benchmark sources differ: {relative}")
            binaries = {}
            for name, root in roots.items():
                binary = Path(directory) / f"{name}-{source.stem}"
                subprocess.run([*ard, "build", str(relative), "--out", str(binary)], cwd=root, check=True)
                binaries[name] = binary
            samples = {name: [] for name in roots}
            for iteration in range(args.warmups + args.samples):
                order = list(roots)
                if iteration % 2:
                    order.reverse()
                for name in order:
                    output = subprocess.check_output([str(binaries[name])], cwd=roots[name], text=True)
                    metrics = parse_metrics(output)
                    if iteration >= args.warmups:
                        samples[name].append(metrics)
            timings = {}
            for metric in samples["baseline"][0]:
                if not metric.endswith("_us"):
                    observations = [sample[metric] for runs in samples.values() for sample in runs]
                    if any(value != observations[0] for value in observations):
                        raise RuntimeError(f"Observed results differ for {source.name}: {metric}: {observations}")
                    continue
                timings[metric] = {}
                for name, runs in samples.items():
                    values = [run[metric] for run in runs]
                    timings[metric][name] = {
                        "median": statistics.median(values), "min": min(values), "max": max(values)
                    }
            report["workloads"][source.stem] = {
                "source_sha256": hashlib.sha256(contents[0]).hexdigest(),
                "raw": samples, "timings": timings,
            }
            args.output.write_text(json.dumps(report, indent=2) + "\n")
            print(source.stem, flush=True)
            for metric, values in timings.items():
                before, after = values["baseline"]["median"], values["candidate"]["median"]
                ratio = f"{after / before:.2f}x" if before else "n/a"
                print(f"  {metric:32} {before:10g} -> {after:10g} us ({ratio})", flush=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
