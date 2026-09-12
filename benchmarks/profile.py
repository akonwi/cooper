#!/usr/bin/env python3
"""Build identical Ard workloads, compare batches, then collect Go profiles.

No production instrumentation: the Go runner replaces only generated main.go.
Run exclusively; do not compile another Ard target in either checkout concurrently.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import statistics
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
PHASES = ("layout_update", "layout_unchanged", "render_update", "render_unchanged")


def command(args, cwd=None):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=25)
    parser.add_argument("--operations", type=int, default=1000)
    parser.add_argument("--profile-seconds", type=float, default=5)
    args = parser.parse_args()
    if args.samples < 1 or args.operations < 1 or args.profile_seconds <= 0:
        parser.error("sample, operation and duration values must be positive")
    roots = {"baseline": args.baseline.resolve(), "candidate": args.candidate.resolve()}
    if roots["baseline"] == roots["candidate"]:
        parser.error("checkouts must be distinct")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    ard = shlex.split(os.environ.get("ARD", "ard"))
    source = (HERE / "profile_layout.ard").read_bytes()
    runner = (HERE / "profile_runner.go.template").read_bytes()
    report = {
        "compiler": command([*ard, "version"]), "go": command(["go", "version"]),
        "host": platform.platform(), "cpu_count": os.cpu_count(),
        "environment": {key: os.environ.get(key, "default") for key in
                        ("GOMAXPROCS", "GOGC", "GOMEMLIMIT", "CGO_ENABLED")},
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "runner_sha256": hashlib.sha256(runner).hexdigest(),
        "revisions": {name: command(["git", "rev-parse", "HEAD"], root) for name, root in roots.items()},
        "tracked_diff_sha256": {name: hashlib.sha256(subprocess.check_output(
            ["git", "diff", "HEAD"], cwd=root)).hexdigest() for name, root in roots.items()},
        "samples": args.samples, "operations": args.operations, "phases": {},
    }
    added = []
    try:
        with tempfile.TemporaryDirectory(prefix="cooper-profiler-") as directory:
            binaries = {}
            for name, root in roots.items():
                target = root / "benchmarks/profile_layout.ard"
                if target.exists():
                    if target.read_bytes() != source:
                        raise RuntimeError(f"Different profiling source: {target}")
                else:
                    target.write_bytes(source)
                    added.append(target)
                binary = Path(directory) / name
                subprocess.run([*ard, "build", str(target), "--out", str(binary)], cwd=root, check=True)
                generated = root / "ard-out/go/build"
                main_file = generated / "main.go"
                original = main_file.read_bytes()
                try:
                    main_file.write_bytes(runner)
                    subprocess.run(["go", "build", "-o", str(binary), "."], cwd=generated, check=True)
                finally:
                    main_file.write_bytes(original)
                binaries[name] = binary

            # All unprofiled timing completes before any profiled run begins.
            for phase in PHASES:
                raw = {name: [] for name in roots}
                for sample in range(args.samples + 3):
                    order = list(roots) if sample % 2 == 0 else list(reversed(roots))
                    for name in order:
                        value = json.loads(command([str(binaries[name]), "-phase", phase, "-n", str(args.operations)]))
                        if not value["verified"]:
                            raise RuntimeError("Unverified profile workload")
                        if sample >= 3:
                            raw[name].append(value)
                summary = {}
                for name, values in raw.items():
                    summary[name] = {}
                    for metric in ("ns_per_op", "go_bytes_per_op", "go_allocs_per_op"):
                        ordered = sorted(value[metric] for value in values)
                        summary[name][metric] = {
                            "median": statistics.median(ordered), "min": ordered[0],
                            "p95": ordered[max(0, (len(ordered) * 95 + 99) // 100 - 1)],
                        }
                report["phases"][phase] = {"raw": raw, "summary": summary}
                (output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
                print(phase, json.dumps(summary), flush=True)

            for phase in PHASES:
                for name, binary in binaries.items():
                    ns = report["phases"][phase]["summary"][name]["ns_per_op"]["median"]
                    count = max(args.operations, int(args.profile_seconds * 1e9 / max(1, ns)))
                    prefix = output / f"{name}-{phase}"
                    command([str(binary), "-phase", phase, "-n", str(count), "-cpu", str(prefix) + ".cpu"])
                    command([str(binary), "-phase", phase, "-n", str(args.operations), "-alloc", str(prefix)])
                    for label, flags in {
                        "cpu-flat": ["-top", "-nodecount=25", str(prefix) + ".cpu"],
                        "cpu-cumulative": ["-top", "-cum", "-nodecount=25", str(prefix) + ".cpu"],
                        "alloc-space": ["-top", "-alloc_space", "-nodecount=25", "-base", str(prefix) + ".before", str(prefix) + ".after"],
                    }.items():
                        (output / f"{name}-{phase}-{label}.txt").write_text(command(["go", "tool", "pprof", *flags]) + "\n")
    finally:
        for target in added:
            target.unlink()


if __name__ == "__main__":
    main()
