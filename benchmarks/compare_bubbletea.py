#!/usr/bin/env python3
"""Compare Cooper main/port and the pinned Bubble Tea/Bubbles pager pattern.

All three binaries use the same driver, data, independent frame oracle and
timing boundaries. This measures headless view generation, not terminal output.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import tempfile

from complex_feed import distribution, read_command

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--samples", type=int, default=30)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.samples < 1:
        parser.error("samples must be positive")
    roots = {"main": args.baseline.resolve(), "ard": args.candidate.resolve()}
    if roots["main"] == roots["ard"]:
        parser.error("distinct Cooper checkouts required")
    native = HERE / "bubbletea_pager"
    source = (HERE / "pager_reference.ard").read_bytes()
    driver = (native / "main.go").read_bytes()
    adapter = (native / "cooper.go.template").read_bytes()
    report = {
        "measurement_protocol": "isolated-verification-v2",
        "revisions": {name: read_command(["git", "rev-parse", "HEAD"], root) for name,root in roots.items()},
        "compiler": read_command(["ard", "version"]), "go": read_command(["go", "version"]),
        "platform": platform.platform(), "cpus": os.cpu_count(),
        "environment": {key: os.environ.get(key, "default") for key in ("GOMAXPROCS", "GOGC", "CGO_ENABLED")},
        "modules": read_command(["go", "list", "-m", "all"], native),
        "hashes": {str(path.relative_to(HERE)): hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in [HERE / "pager_reference.ard", native / "main.go", native / "cooper.go.template",
                                native / "bubbletea.go", native / "go.mod", native / "go.sum"]},
        "sessions": args.samples, "raw": {name: [] for name in [*roots, "bubbletea"]},
        "validation": {name: [] for name in [*roots, "bubbletea"]},
    }
    created = []
    reference = None
    try:
        with tempfile.TemporaryDirectory(prefix="cooper-bubbletea-") as directory:
            binaries = {}
            for name, root in roots.items():
                target = root / "benchmarks/pager_reference.ard"
                if target.exists():
                    if target.read_bytes() != source:
                        raise RuntimeError(f"different fixture: {target}")
                else:
                    target.write_bytes(source)
                    created.append(target)
                binary = Path(directory) / name
                subprocess.run(["ard", "build", str(target), "--out", str(binary)], cwd=root, check=True)
                generated = root / "ard-out/go/build"
                entry = generated / "main.go"
                bridge = generated / "benchmark_adapter.go"
                if bridge.exists():
                    raise RuntimeError(f"unexpected generated adapter: {bridge}")
                original = entry.read_bytes()
                try:
                    entry.write_bytes(driver)
                    bridge.write_bytes(adapter)
                    subprocess.run(["go", "build", "-o", str(binary), "."], cwd=generated, check=True)
                finally:
                    entry.write_bytes(original)
                    bridge.unlink()
                binaries[name] = binary
            binaries["bubbletea"] = Path(directory) / "bubbletea"
            subprocess.run(["go", "build", "-mod=readonly", "-o", str(binaries["bubbletea"]), "."], cwd=native, check=True)
            for iteration in range(args.samples + 3):
                order = list(binaries)
                offset = iteration % len(order)
                order = order[offset:] + order[:offset]
                for name in order:
                    validation = json.loads(read_command([str(binaries[name]), "-verify"]))
                    samples = validation["samples"]
                    if validation["verify"] is not True:
                        raise RuntimeError("expected verification process")
                    if [s["kind"] for s in samples] != ["down"]*100 + ["up"]*100 + ["unchanged"]*40:
                        raise RuntimeError("incomplete pager session")
                    frames = [s["frame_sha256"] for s in samples]
                    if reference is None:
                        reference = frames
                    if frames != reference:
                        raise RuntimeError(f"cross-framework frame mismatch: {name}/{iteration}")
                    result = json.loads(read_command([str(binaries[name])]))
                    if result["verify"] is not False or [s["kind"] for s in result["samples"]] != [s["kind"] for s in samples]:
                        raise RuntimeError("incomplete measurement session")
                    if any("frame_sha256" in s for s in result["samples"]):
                        raise RuntimeError("measurement process performed inter-step verification")
                    if validation["final_frame_sha256"] != frames[-1] or result["final_frame_sha256"] != frames[-1]:
                        raise RuntimeError("measurement final frame differs from verified sequence")
                    if iteration >= 3:
                        report["raw"][name].append(result)
                        report["validation"][name].append(validation)
                print(f"session {iteration+1}: 720 frame checks passed", flush=True)
            report["summary"] = {}
            for name, sessions in report["raw"].items():
                report["summary"][name] = {"startup_ns": distribution([s["startup_ns"] for s in sessions])}
                for kind in ["down", "up", "unchanged"]:
                    steps = [s for run in sessions for s in run["samples"] if s["kind"] == kind]
                    report["summary"][name][kind] = {
                        key: distribution([s[key] for s in steps]) for key in ["ns", "go_bytes", "go_allocations"]}
                    report["summary"][name][kind]["gc_cycles"] = sum(s["gc_cycles"] for s in steps)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps(report["summary"], indent=2))
    finally:
        for target in created:
            target.unlink()


if __name__ == "__main__":
    main()
