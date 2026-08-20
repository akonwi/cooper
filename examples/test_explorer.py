#!/usr/bin/env python3
"""Smoke test for the asynchronous Miller-column filesystem explorer."""

import os
import signal
import sys

from test_harness import Screen, build, read_for, send, spawn, wait_exit, wait_for

ROOT = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(ROOT, "explorer")


def click(fd, col, row):
    send(fd, f"\x1b[<0;{col + 1};{row + 1}M")


def main():
    build("explorer")
    pid, fd = spawn(BIN, rows=12, cols=80)
    screen = Screen(12, 80)
    try:
        wait_for(fd, screen, "ard-out/")

        # Enter on an empty filtered list must not open the stale selection.
        send(fd, "/")
        send(fd, "no-such-entry")
        wait_for(fd, screen, "no matches")
        send(fd, "\r")
        wait_for(fd, screen, "/ no-such-entry")
        send(fd, "\x1b")
        wait_for(fd, screen, "/ search")

        # Slash moves focus into the retained Input and filters the active pane.
        send(fd, "/")
        send(fd, "scroll")
        wait_for(fd, screen, "> scroll_form")
        wait_for(fd, screen, "/ scroll")
        read_for(fd, screen, 0.1)
        assert (screen.row, screen.col) == (11, 8), "search Input did not receive focus"

        # Escape restores list focus and the unfiltered directory.
        send(fd, "\x1b")
        wait_for(fd, screen, "/ search")
        wait_for(fd, screen, "ard-out/")

        # A mouse press selects the directory and opens its detail column.
        click(fd, col=0, row=2)
        wait_for(fd, screen, "go/")
        wait_for(fd, screen, "│")

        # Left closes the detail column and restores the parent selection.
        send(fd, "\x1b[D")
        wait_for(fd, screen, "> ard-out/")

        # Keyboard navigation can open the directory again.
        send(fd, "\x1b[C")
        wait_for(fd, screen, "go/")

        send(fd, "\x03")
        status = wait_exit(pid, fd, screen, timeout=2.0)
        if status is None:
            raise AssertionError("Cooper explorer did not exit after Ctrl+C")
        assert status == 0, f"exit status {status}"

        print("✓ Cooper filesystem explorer smoke test passed")
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
