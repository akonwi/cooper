#!/usr/bin/env python3
"""PTY smoke test for the declarative keyed-jobs example."""

import os
import signal

from test_harness import Screen, binary_path, build, drain, resize, send, spawn, wait_exit, wait_for

ROOT = os.path.dirname(os.path.abspath(__file__))
BIN = binary_path("declarative_jobs")


def main():
    os.chdir(ROOT)
    build("declarative_jobs")
    pid, fd = spawn(BIN, rows=18, cols=90)
    screen = Screen(18, 90)
    try:
        wait_for(fd, screen, "DECLARATIVE JOBS")
        wait_for(fd, screen, "Beta deploy · queued")

        send(fd, "release-ready")
        wait_for(fd, screen, "Alpha build · running · note: release-ready")

        send(fd, "\x1bOQ")  # F2: toggle details on the focused Alpha row.
        wait_for(fd, screen, "details: alpha keeps component-local state")

        send(fd, "\x1bOR")  # F3: keyed reorder preserves Alpha's Input.
        drain(fd, screen, 0.2)
        text = screen.text()
        assert text.index("Beta deploy · queued") < text.index("Alpha build · running")
        assert "note: release-ready" in text
        send(fd, "!")
        wait_for(fd, screen, "note: release-ready!")

        send(fd, "\x1bOS")  # F4: remove the other row.
        drain(fd, screen, 0.2)
        assert "Beta deploy · queued" not in screen.text()
        send(fd, "\x1bOS")  # Reinsert Beta as a fresh keyed incarnation.
        wait_for(fd, screen, "Beta deploy · queued · note:")
        assert "note: release-ready!" in screen.text()

        resize(fd, rows=12, cols=72)
        compact = Screen(12, 72)
        wait_for(fd, compact, "Alpha build · running")
        assert "release-ready!" in compact.text()

        send(fd, "\x03")
        status = wait_exit(pid, fd, compact)
        assert status is not None, "declarative jobs did not exit on Ctrl+C"
        assert os.waitstatus_to_exitcode(status) == 0
    finally:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
        except (ProcessLookupError, ChildProcessError):
            pass

    print("declarative jobs PTY smoke test passed")


if __name__ == "__main__":
    main()
