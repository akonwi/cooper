#!/usr/bin/env python3
"""Compare identical public layout inputs with Cooper's pinned Tess checkpoint."""

import argparse
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


BASELINE = "650013dc9525c504b42089cb5c30ddd54e3c5ff0"
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "test/layout_reference.ard"

# Independently calculated cell rectangles: x, y, width, height.
# Grow: max16 leaves44 in ratio1:3. Shrink: min70 leaves20.
SHARED = {
    "grow.a": [0, 0, 11, 4],
    "grow.b": [11, 0, 16, 4],
    "grow.c": [27, 0, 33, 4],
    "shrink.a": [0, 0, 70, 4],
    "shrink.b": [70, 0, 20, 4],
    "reparent": [0, 0, 10, 6],
    "resize": [0, 0, 7, 4],
    "zero": [0, 0, 0, 0],
    "text.initial": [0, 0, 3, 1],
    "text.changed": [0, 0, 5, 2],
    "text.tail": [0, 2, 2, 1],
    "text.unchanged": [0, 0, 5, 2],
    "text.resized": [0, 0, 9, 1],
    "text.resized_tail": [0, 1, 2, 1],
}
ADAPTATIONS = {
    "adr0016.max_content": {
        "baseline": [0, 0, 5, 2],
        "candidate": [0, 0, 9, 1],
    },
}


def parse(output):
    observations = {}
    for line in output.splitlines():
        name, *values = line.split()
        if name in observations or len(values) != 4:
            raise ValueError(f"Invalid or duplicate observation: {line}")
        observations[name] = list(map(int, values))
    return observations


def verify(observations, backend):
    expected = SHARED | {name: values[backend] for name, values in ADAPTATIONS.items()}
    if observations.keys() != expected.keys():
        raise AssertionError(f"{backend}: missing or extra observations: {observations.keys() ^ expected.keys()}")
    for name, rect in expected.items():
        if observations[name] != rect:
            raise AssertionError(f"{backend} {name}: expected {rect}, got {observations[name]}")


def compare_numeric(baseline, scratch):
    tess = Path(subprocess.check_output(
        ["go", "list", "-m", "-f", "{{.Dir}}", "github.com/AnatoleLucet/tess"],
        cwd=baseline, text=True,
    ).strip())
    yoga_revision = (tess / "etc/YOGA_VERSION").read_text().strip()
    if yoga_revision != "8ba025e":
        raise AssertionError(f"Unexpected Yoga reference: {yoga_revision}")
    cpp = scratch / "numeric-cpp"
    ard = scratch / "numeric-ard"
    platform = "_".join(subprocess.check_output(["go", "env", "GOOS", "GOARCH"], text=True).split())
    archive = tess / "etc/lib" / platform / "libyogacore.a"
    subprocess.run([
        "c++", "-std=c++20", "-I", str(tess / "etc/include"),
        str(ROOT / "test/layout_numeric_reference.cpp"),
        str(tess / "etc/include/yoga/algorithm/Cache.cpp"), str(archive), "-o", str(cpp),
    ], check=True)
    subprocess.run([
        "ard", "build", "test/layout_numeric_reference.ard", "--out", str(ard),
    ], cwd=ROOT, check=True)
    reference = subprocess.check_output([str(cpp)], text=True).splitlines()
    candidate = subprocess.check_output([str(ard)], text=True).splitlines()
    if len(reference) != 169 + 12 + 5184 + 5 or candidate != reference:
        difference = "\n".join(difflib.unified_diff(reference, candidate, fromfile="Yoga", tofile="Ard"))
        raise AssertionError(f"Numeric reference mismatch:\n{difference}")
    return {
        "yoga_revision": yoga_revision,
        "header_sha256": hashlib.sha256((tess / "etc/include/yoga/numeric/Comparison.h").read_bytes()).hexdigest(),
        "cache_source_sha256": hashlib.sha256((tess / "etc/include/yoga/algorithm/Cache.cpp").read_bytes()).hexdigest(),
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "sources_sha256": {
            path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for path in (
                "core/layout/numeric.ard", "core/layout/cache.ard", "test/layout_numeric_reference.ard",
                "test/layout_numeric_reference.cpp", "core/layout/measure.ard", "core/layout.ard",
            )
        },
        "pairs": 169,
        "rounding_cases": 12,
        "cache_cases": 5184,
        "leaf_visits": 5,
        "observations": candidate,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional JSON evidence file")
    args = parser.parse_args()
    source = SOURCE.read_bytes()
    report = {
        "baseline": BASELINE,
        "candidate": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "candidate_tracked_diff_sha256": hashlib.sha256(
            subprocess.check_output(["git", "diff", "HEAD"], cwd=ROOT)
        ).hexdigest(),
        "compiler": subprocess.check_output(["ard", "version"], text=True).strip(),
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "observations": {},
    }
    with tempfile.TemporaryDirectory(prefix="cooper-layout-reference-") as directory:
        scratch = Path(directory)
        baseline = scratch / "baseline"
        subprocess.run(["git", "worktree", "add", "--detach", str(baseline), BASELINE], cwd=ROOT, check=True)
        try:
            # Both binaries compile exactly the same source against their own
            # Cooper checkout; no production backend switch or stale fixture.
            target = baseline / SOURCE.relative_to(ROOT)
            if target.exists():
                raise RuntimeError(f"Reference fixture would overwrite {target}")
            target.write_bytes(source)
            for backend, root in [("baseline", baseline), ("candidate", ROOT)]:
                binary = scratch / f"{backend}-program"
                subprocess.run(["ard", "build", str(SOURCE.relative_to(ROOT)), "--out", str(binary)], cwd=root, check=True)
                observations = parse(subprocess.check_output([str(binary)], cwd=root, text=True))
                verify(observations, backend)
                report["observations"][backend] = observations
            report["numeric"] = compare_numeric(baseline, scratch)
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(baseline)], cwd=ROOT, check=True)
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"PASS: {len(SHARED)} shared geometry observations; {len(ADAPTATIONS)} explicit ADR adaptation(s)")
    print(f"PASS: {report['numeric']['pairs']} Float32 operand pairs match pinned Yoga numeric/Comparison.h")
    print(f"PASS: {report['numeric']['cache_cases']} cache decisions and {report['numeric']['rounding_cases']} rounded constraints match pinned Yoga")
    print(f"PASS: {report['numeric']['leaf_visits']} cached leaf visits match pinned Yoga dimensions, dirtiness and callback counts")


if __name__ == "__main__":
    main()
