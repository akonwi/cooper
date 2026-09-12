#!/usr/bin/env python3
"""Profile repeated pager/feed scroll sequences, excluding setup and verification.

Run without competing builds/tests. Use compare_bubbletea.py and complex_feed.py
for latency comparisons; these longer-lived sessions are diagnostic only.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


HERE = Path(__file__).resolve().parent
DRIVER = r'''package main
import (
  "flag"
  "fmt"
  fixture "github.com/akonwi/cooper/benchmarks/FIXTURE"
  "os"
  "runtime"
  "runtime/pprof"
  "strings"
  "time"
)
func snapshot(path string) {
  f, err := os.Create(path); if err != nil { panic(err) }; defer f.Close()
  if err := pprof.Lookup("allocs").WriteTo(f, 0); err != nil { panic(err) }
}
func main() {
  seconds := flag.Duration("duration", 5*time.Second, "profile duration")
  cpu := flag.String("cpu", "", "CPU profile")
  alloc := flag.String("alloc", "", "allocation profile prefix")
  eager := flag.Bool("eager", false, "mount all feed cards")
  flag.Parse()
  if *alloc != "" { runtime.MemProfileRate = 4096 }
  // PREPARE
  defer closeSession()
  _ = strings.Repeat; _ = eager
  for i := 0; i < count; i++ { step(i) }
  initial := verify()
  runtime.GC()
  if *alloc != "" { snapshot(*alloc+".before") }
  if *cpu != "" {
    f, err := os.Create(*cpu); if err != nil { panic(err) }; defer f.Close()
    if err := pprof.StartCPUProfile(f); err != nil { panic(err) }
  }
  start := time.Now()
  operations := 0
  for time.Since(start) < *seconds {
    for i := 0; i < count; i++ { step(i); operations++ }
  }
  if *cpu != "" { pprof.StopCPUProfile() }
  if *alloc != "" { runtime.GC(); snapshot(*alloc+".after") }
  if verify() != initial { panic("repeated sequence did not return to its initial frame") }
  fmt.Printf("%d operations; final frame verified\n", operations)
}
'''
PAGER = r'''
  lines := make([]string, 10000)
  for i := range lines { lines[i] = fmt.Sprintf("%05d | %s", i, strings.Repeat("abcdefghij", 1+(i*37)%14)) }
  model := fixture.Prepare(lines)
  count := 240
  step := func(i int) { direction := 1; if i >= 100 { direction = -1 }; if i >= 200 { direction = 0 }; model.Step(direction) }
  verify, closeSession := model.View, model.Close
'''
FEED = r'''
  model := fixture.Prepare(*eager)
  count := 40
  step, verify, closeSession := model.Step, model.Verify, model.Close
'''


def run(args, cwd=None):
    return subprocess.check_output(args, cwd=cwd, text=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=5)
    args = parser.parse_args()
    if args.seconds <= 0:
        parser.error("seconds must be positive")
    root = HERE.parent
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = {"revision": run(["git", "rev-parse", "HEAD"], root).strip(),
              "diff_sha256": hashlib.sha256(subprocess.check_output(["git", "diff", "HEAD"], cwd=root)).hexdigest(),
              "compiler": run(["ard", "version"]).strip(), "go": run(["go", "version"]).strip(),
              "seconds": args.seconds, "workloads": {}}
    with tempfile.TemporaryDirectory(prefix="cooper-text-profile-") as temporary:
        for fixture, prepare, modes in (("pager_reference", PAGER, ("pager",)),
                                        ("complex_feed", FEED, ("lazy", "eager"))):
            subprocess.run(["ard", "build", str(HERE / (fixture+".ard")), "--out", temporary+"/fixture"], cwd=root, check=True)
            driver = Path(temporary) / "main.go"
            driver.write_text(DRIVER.replace("FIXTURE", fixture).replace("// PREPARE", prepare))
            binary = output / fixture
            subprocess.run(["go", "build", "-o", binary, driver], cwd=root / "ard-out/go/build", check=True)
            for mode in modes:
                common = [str(binary), f"-duration={args.seconds}s", f"-eager={str(mode == 'eager').lower()}"]
                cpu, alloc = output / (mode+".cpu"), output / (mode+".alloc")
                cpu_result = run([*common, "-cpu", str(cpu)])
                alloc_result = run([*common, "-alloc", str(alloc)])
                for suffix, options in (("cpu", [str(cpu)]),
                                        ("alloc", ["-alloc_space", "-base", str(alloc)+".before", str(alloc)+".after"])):
                    for cumulative in (False, True):
                        text = run(["go", "tool", "pprof", "-top", *(["-cum"] if cumulative else []), *options[:-1], str(binary), options[-1]])
                        (output / f"{mode}.{suffix}{'-cum' if cumulative else ''}.txt").write_text(text)
                report["workloads"][mode] = {"cpu": cpu_result.strip(), "alloc": alloc_result.strip()}
                print(mode, report["workloads"][mode], flush=True)
    (output / "report.json").write_text(json.dumps(report, indent=2)+"\n")


if __name__ == "__main__":
    main()
