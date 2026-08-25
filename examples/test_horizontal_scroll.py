#!/usr/bin/env python3
"""PTY validation for Cooper's built-in two-axis ScrollBox bars."""

import os
import signal
import sys

from test_harness import Screen, binary_path, build, send, spawn, wait_exit, wait_for

ROOT = os.path.dirname(os.path.abspath(__file__))
BIN = binary_path("horizontal_scroll")


def sgr(fd, code, col, row, suffix="M"):
    send(fd, f"\x1b[<{code};{col + 1};{row + 1}{suffix}")


def drag(fd, start_col, start_row, end_col, end_row):
    sgr(fd, 0, start_col, start_row)
    sgr(fd, 32, end_col, end_row)
    sgr(fd, 0, end_col, end_row, "m")


def main():
    os.chdir(ROOT)
    build("horizontal_scroll", source="fixtures/horizontal_scroll.ard")
    pid, fd = spawn(BIN, rows=6, cols=20)
    screen = Screen(6, 20)
    try:
        wait_for(fd, screen, "0:ABCDEFGHI")
        assert screen.line(5).startswith("━━━━━━"), screen.text()
        assert screen.line(5).endswith("│"), screen.text()

        drag(fd, start_col=0, start_row=5, end_col=18, end_row=5)
        wait_for(fd, screen, "nopqr")

        drag(fd, start_col=18, start_row=5, end_col=0, end_row=5)
        wait_for(fd, screen, "0:ABCDEFGHI")

        drag(fd, start_col=19, start_row=0, end_col=19, end_row=5)
        wait_for(fd, screen, "3:ABCDEFGHI")

        # SGR Shift+wheel-down maps vertical wheel motion onto horizontal state.
        sgr(fd, 69, 0, 0)
        wait_for(fd, screen, "BCDEFG")
        send(fd, "\x1b[C")
        wait_for(fd, screen, "CDEFGH")

        send(fd, "\x03")
        status = wait_exit(pid, fd, screen, timeout=2.0)
        if status is None:
            raise AssertionError("horizontal scroll fixture did not exit")
        assert status == 0, f"exit status {status}"
        print("✓ Cooper two-axis ScrollBox PTY test passed")
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
