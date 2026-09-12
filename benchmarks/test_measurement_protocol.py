import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def run(binary, mode, fail=None):
    env = os.environ.copy()
    env["PROTOCOL_MODE"] = mode
    if fail is not None:
        env["PROTOCOL_FAIL_STEP"] = str(fail)
    args = [str(binary)] + (["-verify"] if mode == "verify" else [])
    return subprocess.run(args, text=True, capture_output=True, env=env)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class MeasurementProtocolTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        root = Path(cls.temp.name)

        pager = root / "pager"
        pager.mkdir()
        shutil.copy(ROOT / "benchmarks/bubbletea_pager/main.go", pager / "main.go")
        (pager / "adapter.go").write_text(r'''package main
import ("fmt"; "os"; "strconv"; "strings"; "time")
func prepare(lines []string) session {
  offset, steps := 0, 0
  step := func(direction int) { time.Sleep(time.Microsecond); offset += direction; steps++ }
  view := func() string {
    if os.Getenv("PROTOCOL_MODE") == "measured" && steps < 240 { panic("measured serialized early") }
    rows := make([]string, 24)
    for i := range rows { row := lines[offset+i]; if len(row)>80 { row=row[:80] }; rows[i]=row }
    frame := strings.Join(rows, "\n")
    failText := os.Getenv("PROTOCOL_FAIL_STEP"); fail, _ := strconv.Atoi(failText)
    if os.Getenv("PROTOCOL_MODE") == "verify" && failText != "" && steps == fail+1 { frame = "X" + frame[1:] }
    return frame
  }
  return session{step: step, view: view, close: func(){ fmt.Sprint(offset) }}
}
''')
        subprocess.run(["go", "mod", "init", "pager-test"], cwd=pager, check=True,
                       capture_output=True)
        cls.pager = root / "pager-driver"
        subprocess.run(["go", "build", "-o", cls.pager, "."], cwd=pager, check=True)

        feed = root / "feed"
        (feed / "benchmarks/complex_feed").mkdir(parents=True)
        shutil.copy(ROOT / "benchmarks/complex_feed_runner.go.template", feed / "main.go")
        (feed / "go.mod").write_text("module github.com/akonwi/cooper\n\ngo 1.22\n")
        (feed / "benchmarks/complex_feed/stub.go").write_text(r'''package complex_feed
import ("fmt"; "os"; "strconv"; "time")
type Session struct { current int }
func Prepare(eager bool) *Session { return &Session{current: -1} }
func (s *Session) Step(i int) { if i != s.current+1 { panic("steps out of order") }; time.Sleep(time.Microsecond); s.current=i }
func (s *Session) Verify() string {
  if os.Getenv("PROTOCOL_MODE") == "measured" && s.current < 39 { panic("measured serialized early") }
  failText := os.Getenv("PROTOCOL_FAIL_STEP"); fail, _ := strconv.Atoi(failText)
  if os.Getenv("PROTOCOL_MODE") == "verify" && failText != "" && s.current == fail { panic("injected intermediate failure") }
  return fmt.Sprintf("frame-%d", s.current)
}
func (s *Session) Close() {}
''')
        cls.feed = root / "feed-driver"
        subprocess.run(["go", "build", "-o", cls.feed, "."], cwd=feed, check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def assert_samples(self, result, count, expected_order, verify):
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["verify"], verify)
        self.assertEqual(len(data["samples"]), count)
        self.assertEqual(expected_order(data["samples"]), list(range(count)))
        for sample in data["samples"]:
            self.assertEqual("frame_sha256" in sample, verify)
            if verify:
                self.assertEqual(sample["ns"], 0)
                self.assertEqual(len(sample["frame_sha256"]), 64)
            else:
                self.assertGreater(sample["ns"], 0)
        return data

    def test_pager_measurement_and_verification_are_split(self):
        measured = self.assert_samples(run(self.pager, "measured", 37), 240,
            lambda samples: list(range(len(samples))), False)
        verify = self.assert_samples(run(self.pager, "verify"), 240,
            lambda samples: list(range(len(samples))), True)
        kinds = ["down"] * 100 + ["up"] * 100 + ["unchanged"] * 40
        self.assertEqual([s["kind"] for s in measured["samples"]], kinds)
        self.assertEqual([s["kind"] for s in verify["samples"]], kinds)
        lines = [f"{i:05d} | " + "abcdefghij" * (1 + (i * 37) % 14) for i in range(24)]
        final = "\n".join(line[:80].ljust(80) for line in lines)
        self.assertEqual(measured["final_frame_sha256"], digest(final))
        self.assertEqual(verify["final_frame_sha256"], digest(final))
        failed = run(self.pager, "verify", 37)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn("step 37", failed.stderr)

    def test_feed_measurement_and_verification_are_split(self):
        measured = self.assert_samples(run(self.feed, "measured", 17), 40,
            lambda samples: [s["step"] for s in samples], False)
        verify = self.assert_samples(run(self.feed, "verify"), 40,
            lambda samples: [s["step"] for s in samples], True)
        self.assertEqual(measured["final_frame_sha256"], digest("frame-39"))
        self.assertEqual(verify["final_frame_sha256"], digest("frame-39"))
        failed = run(self.feed, "verify", 17)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn("injected intermediate failure", failed.stderr)


if __name__ == "__main__":
    unittest.main()
