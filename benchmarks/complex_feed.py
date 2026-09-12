#!/usr/bin/env python3
"""Compare a nested scrolling feed against another Cooper checkout.

Each 40-step session is checked cell-for-cell across lazy/eager and both branches.
Run without competing builds/benchmarks. Requires Ard's generated Go build tree.
"""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent


def read_command(args, cwd=None):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def distribution(values):
    values = sorted(values)
    return {"median": statistics.median(values), "p95": values[(len(values)*95+99)//100-1],
            "p99": values[(len(values)*99+99)//100-1], "max": values[-1]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--samples", type=int, default=30)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.samples < 1:
        parser.error("samples must be positive")
    roots = {"baseline": args.baseline.resolve(), "candidate": args.candidate.resolve()}
    if roots["baseline"] == roots["candidate"]:
        parser.error("distinct checkouts required")
    source = (HERE / "complex_feed.ard").read_bytes()
    runner = (HERE / "complex_feed_runner.go.template").read_bytes()
    report = {"measurement_protocol": "isolated-verification-v2",
              "revisions": {k: read_command(["git", "rev-parse", "HEAD"], v) for k,v in roots.items()},
              "compiler": read_command(["ard", "version"]), "go": read_command(["go", "version"]),
              "source_sha256": hashlib.sha256(source).hexdigest(),
              "runner_sha256": hashlib.sha256(runner).hexdigest(), "sessions": args.samples,
              "raw": {k: {m: [] for m in ("lazy", "eager")} for k in roots},
              "validation": {k: {m: [] for m in ("lazy", "eager")} for k in roots}}
    created = []
    expected = None
    try:
        with tempfile.TemporaryDirectory(prefix="cooper-complex-") as directory:
            binaries = {}
            for name, root in roots.items():
                target = root / "benchmarks/complex_feed.ard"
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
                original = entry.read_bytes()
                try:
                    entry.write_bytes(runner)
                    subprocess.run(["go", "build", "-o", str(binary), "."], cwd=generated, check=True)
                finally:
                    entry.write_bytes(original)
                binaries[name] = binary
            for iteration in range(args.samples + 3):
                branches = list(roots) if iteration % 2 == 0 else list(reversed(roots))
                modes = ("lazy", "eager") if iteration % 2 == 0 else ("eager", "lazy")
                for name in branches:
                    for mode in modes:
                        command = [str(binaries[name]), f"-eager={str(mode == 'eager').lower()}"]
                        validation = json.loads(read_command([*command, "-verify"]))
                        steps = validation["samples"]
                        if validation["verify"] is not True:
                            raise RuntimeError("expected verification process")
                        if [step["step"] for step in steps] != list(range(40)):
                            raise RuntimeError("incomplete scroll session")
                        frames = [step["frame_sha256"] for step in steps]
                        if expected is None:
                            expected = frames
                            reference_capture = validation["capture"]
                        if frames != expected:
                            print("\n".join(difflib.unified_diff(reference_capture.splitlines(), validation["capture"].splitlines(), fromfile="baseline", tofile=f"{name}/{mode}")))
                            raise RuntimeError(f"frame mismatch: {name}/{mode}/{iteration}")
                        result = json.loads(read_command(command))
                        if result["verify"] is not False or [s["step"] for s in result["samples"]] != list(range(40)):
                            raise RuntimeError("incomplete measurement session")
                        if any("frame_sha256" in s for s in result["samples"]):
                            raise RuntimeError("measurement process performed inter-step verification")
                        if validation["final_frame_sha256"] != frames[-1] or result["final_frame_sha256"] != frames[-1]:
                            raise RuntimeError("measurement final frame differs from verified sequence")
                        if iteration >= 3:
                            report["raw"][name][mode].append(result)
                            report["validation"][name][mode].append(validation)
                print(f"session {iteration + 1}: all 160 frame checks passed", flush=True)
            report["summary"] = {}
            for name, modes in report["raw"].items():
                report["summary"][name] = {}
                for mode, sessions in modes.items():
                    steps = [step for session in sessions for step in session["samples"]]
                    report["summary"][name][mode] = {
                        "scroll_ns": distribution([step["ns"] for step in steps]),
                        "go_bytes": distribution([step["go_bytes"] for step in steps]),
                        "go_allocations": distribution([step["go_allocations"] for step in steps]),
                        "startup_ns": distribution([session["startup_ns"] for session in sessions]),
                        "gc_cycles": sum(step["gc_cycles"] for step in steps),
                    }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps(report["summary"], indent=2))
    finally:
        for path in created:
            path.unlink()


if __name__ == "__main__":
    main()
