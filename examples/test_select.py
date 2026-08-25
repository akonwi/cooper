#!/usr/bin/env python3
"""PTY validation for Cooper's built-in Select menu and TabSelect presentations."""

import os
import signal
import sys

from test_harness import Screen, binary_path, build, drain, resize, send, spawn, wait_exit, wait_for

ROOT = os.path.dirname(os.path.abspath(__file__))
BIN = binary_path("select")


def sgr(fd, code, col, row, suffix="M"):
    send(fd, f"\x1b[<{code};{col + 1};{row + 1}{suffix}")


def click(fd, col, row):
    sgr(fd, 0, col, row)
    sgr(fd, 0, col, row, "m")


def drag(fd, start_col, start_row, end_col, end_row):
    sgr(fd, 0, start_col, start_row)
    sgr(fd, 32, end_col, end_row)
    sgr(fd, 0, end_col, end_row, "m")


def wheel_down(fd, col, row):
    sgr(fd, 65, col, row)


def main():
    os.chdir(ROOT)
    build("select", source="fixtures/select.ard")
    pid, fd = spawn(BIN, rows=24, cols=80)
    screen = Screen(24, 80)
    try:
        wait_for(fd, screen, "BUILT-IN SELECTS")
        wait_for(fd, screen, "Home description")
        drain(fd, screen, 0.2)
        assert "Select…" in screen.line(6), screen.text()
        assert "▾" in screen.line(6), screen.text()

        send(fd, "\x1b[C")
        wait_for(fd, screen, "Tab highlight: Profile · index 1")
        send(fd, "\r")
        wait_for(fd, screen, "Tab submitted: Profile · index 1")

        send(fd, "\t")
        wait_for(fd, screen, "Focus: Select")
        send(fd, "\r")
        wait_for(fd, screen, "Home description")
        send(fd, "\x1b[B")
        drain(fd, screen, 0.1)
        send(fd, "\x1b[1;2B")
        drain(fd, screen, 0.1)
        send(fd, "\r")
        wait_for(fd, screen, "Select submitted: Billing · index 6")

        send(fd, "\r")
        wheel_down(fd, col=10, row=12)
        drain(fd, screen, 0.1)
        drag(fd, start_col=79, start_row=8, end_col=79, end_row=21)
        wait_for(fd, screen, "About description")
        send(fd, "\r")
        wait_for(fd, screen, "Select submitted: Billing · index 6")

        # Clicking the tab header focuses, highlights, selects, and submits it.
        click(fd, col=25, row=2)
        wait_for(fd, screen, "Tab submitted: Settings · index 2")

        resize(fd, rows=18, cols=60)
        compact = Screen(18, 60)
        wait_for(fd, compact, "BUILT-IN SELECTS")
        wait_for(fd, compact, "Settings description")
        drain(fd, compact, 0.1)
        assert "›" in compact.line(2), compact.text()

        send(fd, "\x03")
        status = wait_exit(pid, fd, compact, timeout=2.0)
        if status is None:
            raise AssertionError("Select fixture did not exit")
        assert status == 0, f"exit status {status}"
        print("✓ Cooper built-in Select PTY test passed")
    finally:
        cleanup(fd, pid)


def cleanup(fd, pid):
    try:
        os.close(fd)
    except OSError:
        pass
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"FAIL: {err}", file=sys.stderr)
        sys.exit(1)
