#!/usr/bin/env python3
"""Compare live Go heap after GC and sampled scrolling heap, not latency or RSS."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import tempfile

from complex_feed import distribution, read_command
from profile_text import FEED, PAGER


HERE = Path(__file__).resolve().parent
DRIVER = r'''package main
import (
  "crypto/sha256"
  "encoding/json"
  "flag"
  "fmt"
  fixture "github.com/akonwi/cooper/benchmarks/FIXTURE"
  "os"
  "runtime"
  "strings"
)
func main() {
  eager := flag.Bool("eager", false, "mount all feed cards")
  sequences := flag.Int("sequences", 10, "complete scrolling sequences")
  flag.Parse()
  // PREPARE
  defer closeSession()
  _ = strings.Repeat; _ = eager
  for i := 0; i < count; i++ { step(i) }
  initial := sha256.Sum256([]byte(verify()))
  runtime.GC()
  var warm, current, settled runtime.MemStats
  runtime.ReadMemStats(&warm)
  maxHeap := warm.HeapAlloc
  for sequence := 0; sequence < *sequences; sequence++ {
    for i := 0; i < count; i++ {
      step(i)
      runtime.ReadMemStats(&current)
      if current.HeapAlloc > maxHeap { maxHeap = current.HeapAlloc }
    }
  }
  runtime.GC()
  runtime.ReadMemStats(&settled)
  // Verify only after sampling; keep the live session reachable through GC.
  final := sha256.Sum256([]byte(verify()))
  runtime.KeepAlive(model)
  if final != initial { panic("repeated sequence changed the final frame") }
  json.NewEncoder(os.Stdout).Encode(map[string]any{
    "warm_live_bytes": warm.HeapAlloc,
    "settled_live_bytes": settled.HeapAlloc,
    "settled_heap_inuse_bytes": settled.HeapInuse,
    "sampled_max_heap_bytes": maxHeap,
    "automatic_gc_cycles": current.NumGC - warm.NumGC,
    "operations": count * *sequences,
    "final_frame_sha256": fmt.Sprintf("%x", final),
  })
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--samples", type=int, default=10)
    parser.add_argument("--sequences", type=int, default=10)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.samples < 1 or args.sequences < 1:
        parser.error("samples and sequences must be positive")
    roots = {"baseline": args.baseline.resolve(), "candidate": args.candidate.resolve()}
    if roots["baseline"] == roots["candidate"]:
        parser.error("distinct checkouts required")
    report = {
        "protocol": "settled-live-heap-v1",
        "revisions": {k: read_command(["git", "rev-parse", "HEAD"], v) for k, v in roots.items()},
        "compiler": read_command(["ard", "version"]),
        "go": read_command(["go", "version"]),
        "platform": platform.platform(), "cpus": os.cpu_count(),
        "environment": {k: os.environ.get(k, "default") for k in ("GOGC", "GOMEMLIMIT", "GOMAXPROCS")},
        "samples": args.samples, "sequences": args.sequences,
        "driver_sha256": hashlib.sha256(DRIVER.encode()).hexdigest(),
        "fixture_hashes": {}, "raw": {k: {} for k in roots}, "summary": {k: {} for k in roots},
    }
    with tempfile.TemporaryDirectory(prefix="cooper-heap-") as temporary:
        for fixture, prepare, modes in (("pager_reference", PAGER, ("pager",)),
                                        ("complex_feed", FEED, ("lazy", "eager"))):
            driver = Path(temporary) / "main.go"
            driver.write_text(DRIVER.replace("FIXTURE", fixture).replace("// PREPARE", prepare))
            source = (HERE / (fixture + ".ard")).read_bytes()
            report["fixture_hashes"][fixture] = {
                "source": hashlib.sha256(source).hexdigest(),
                "driver": hashlib.sha256(driver.read_bytes()).hexdigest(),
            }
            binaries = {}
            for name, root in roots.items():
                target = root / "benchmarks" / (fixture + ".ard")
                if target.read_bytes() != source:
                    raise RuntimeError(f"different fixture: {target}")
                binary = Path(temporary) / name
                subprocess.run(["ard", "build", str(target), "--out", str(binary)], cwd=root, check=True)
                subprocess.run(["go", "build", "-o", str(binary), str(driver)],
                               cwd=root / "ard-out/go/build", check=True)
                binaries[name] = binary
            for mode in modes:
                expected = None
                for name in roots:
                    report["raw"][name][mode] = []
                for iteration in range(args.samples):
                    order = list(roots) if iteration % 2 == 0 else list(reversed(roots))
                    for name in order:
                        result = json.loads(read_command([str(binaries[name]),
                            f"-eager={str(mode == 'eager').lower()}", f"-sequences={args.sequences}"]))
                        if expected is None:
                            expected = result["final_frame_sha256"]
                        if result["final_frame_sha256"] != expected:
                            raise RuntimeError(f"frame mismatch: {name}/{mode}/{iteration}")
                        report["raw"][name][mode].append(result)
                    print(f"{mode} sample {iteration + 1}: final frames match", flush=True)
                for name in roots:
                    samples = report["raw"][name][mode]
                    report["summary"][name][mode] = {
                        k: distribution([s[k] for s in samples])
                        for k in samples[0] if k != "final_frame_sha256"
                    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
