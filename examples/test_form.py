#!/usr/bin/env python3
"""Smoke test for Cooper's nested focus routing example."""

import os
import signal
import sys

from test_harness import Screen, build, send, spawn, wait_exit, wait_for

ROOT = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(ROOT, "form")


def main():
    build("form")
    pid, fd = spawn(BIN, rows=14, cols=70)
    screen = Screen(14, 70)
    try:
        wait_for(fd, screen, "Only the focused field")

        send(fd, "Ada")
        wait_for(fd, screen, "Ada")

        # Click the nested Email input (terminal mouse coordinates are 1-based).
        click(fd, col=0, row=6)
        send(fd, "ada@example.com")
        wait_for(fd, screen, "ada@example.com")

        send(fd, "\t")
        send(fd, "Paris")
        wait_for(fd, screen, "Paris")

        # Forward traversal wraps from City to Name. Clicking column zero then
        # proves the Input receives target-local coordinates for cursor placement.
        send(fd, "\t")
        click(fd, col=0, row=4)
        send(fd, "!")
        wait_for(fd, screen, "!Ada")

        # Reverse traversal wraps from Name to City.
        send(fd, "\x1b[Z")
        send(fd, "!")
        wait_for(fd, screen, "Paris!")

        send(fd, "\x03")
        status = wait_exit(pid, fd, screen, timeout=2.0)
        if status is None:
            raise AssertionError("Cooper form did not exit after Ctrl+C")
        assert status == 0, f"exit status {status}"

        print("✓ Cooper focus form smoke test passed")
    finally:
        cleanup(fd, pid)


def click(fd, col, row):
    send(fd, f"\x1b[<0;{col + 1};{row + 1}M")


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
