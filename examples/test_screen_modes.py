#!/usr/bin/env python3
"""Run Cooper against Vaxis's terminal emulator over a real PTY.

Unlike the basic Screen smoke-test model, this peer supports cursor reports,
saved cursor state, resize/reflow, alternate buffers, and scrollback.
"""

import os
import re
import select
import signal
import subprocess
import time

from test_harness import ROOT, build, spawn, _respond_to_queries


def lifecycle(binary, scenario):
    # A protocol peer deliberately withholds CPR. It checks errors and cleanup
    # bytes, not rendered cells or history (the Go terminal-model tests do that).
    pid, fd = spawn(binary, rows=8, cols=48, env={"COOPER_SCREEN_LIFECYCLE": scenario})
    output = bytearray()
    status = None
    pending = b""
    try:
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if select.select([fd], [], [], 0.02)[0]:
                try:
                    data = os.read(fd, 65536)
                except OSError:
                    data = b""
                output.extend(data)
                pending += data
                # Buffer partial escape sequences across PTY reads.
                queries = list(re.finditer(rb"\x1b\[[0-9?=;]*[cnu]", pending))
                replies = b"".join(query.group() for query in queries)
                pending = pending[queries[-1].end():] if queries else pending[-32:]
                if scenario == "startup-failure" or (scenario == "resume-failure" and b"EXTERNAL OUTPUT" in output):
                    replies = replies.replace(b"\x1b[6n", b"")
                _respond_to_queries(fd, replies)
            done, current = os.waitpid(pid, os.WNOHANG)
            if done == pid:
                status = current
                break
        assert status == 0, (scenario, status, bytes(output))
        assert b"LIFECYCLE RESTORED" in output, (scenario, bytes(output))
        # Vaxis probes capabilities in a temporary alternate buffer at New.
        assert output.count(b"\x1b[?1049h") == 1 and output.count(b"\x1b[?1049l") == 1, "unbalanced alternate-buffer capability probe"
        assert b"\x1b[?25h" in output, "cursor visibility not restored"
        if scenario == "prestart":
            normal = bytes(output).split(b"\x1b[?1049l", 1)[1]
            assert b"\x1b[6n" not in normal and b"LIVE REGION" not in normal, "unstarted destruction reserved a surface"
        if scenario in ("suspended", "resume-failure"):
            after = bytes(output).split(b"EXTERNAL OUTPUT", 1)[1]
            assert b"LIVE REGION" not in after, "suspended destruction repainted stale rows"
        print(f"✓ screen lifecycle: {scenario}")
    finally:
        os.close(fd)
        if status is None:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)


def main():
    binary = build("screen_modes")
    subprocess.run(
        ["go", "test", "./fixtures", "-run", "^TestScreen", "-count=1", "-v", "-timeout=90s"],
        cwd=ROOT,
        env=dict(os.environ, COOPER_SCREEN_BINARY=binary),
        check=True,
    )
    binary = build("screen_lifecycle", source="fixtures/screen_lifecycle.ard")
    for scenario in ("prestart", "suspended", "startup-failure", "resume-failure"):
        lifecycle(binary, scenario)


if __name__ == "__main__":
    main()
