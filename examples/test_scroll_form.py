#!/usr/bin/env python3
"""Smoke test for Cooper's retained vertical ScrollView."""

import os
import signal
import sys

from test_harness import Screen, build, drain, resize, send, spawn, wait_exit, wait_for

ROOT = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(ROOT, "scroll_form")


def main():
    build("scroll_form")
    pid, fd = spawn(BIN, rows=8, cols=60)
    screen = Screen(8, 60)
    try:
        wait_for(fd, screen, "Cooper scrolling form")
        wait_for(fd, screen, "Field 3")

        # Tab to the first offscreen Input; the viewport should reveal it.
        send(fd, "\t")
        send(fd, "\t")
        send(fd, "\t")
        wait_for(fd, screen, "Field 4")
        assert screen.line(6).startswith("Field 4"), screen.text()
        assert screen.line(7).startswith("Value 4"), screen.text()

        # A smaller viewport keeps the focused Input visible after resize.
        resize(fd, rows=6, cols=60)
        drain(fd, screen)
        assert screen.line(4).startswith("Field 4"), screen.text()
        assert screen.line(5).startswith("Value 4"), screen.text()
        resize(fd, rows=8, cols=60)
        drain(fd, screen)

        # Reverse traversal reveals a focused target above the viewport.
        send(fd, "\x1b[Z")
        send(fd, "\x1b[Z")
        send(fd, "\x1b[Z")
        drain(fd, screen)
        assert screen.line(3).startswith("Field 2"), screen.text()
        send(fd, "one")
        wait_for(fd, screen, "one")
        assert screen.line(2).startswith("one"), screen.text()

        # Restore the top before exercising routed wheel/click behavior.
        wheel(fd, down=False, col=0, row=3)
        wait_for(fd, screen, "Field 1")

        wheel(fd, down=True, col=0, row=3)
        wait_for(fd, screen, "Field 4")

        # Field 4's Input is the last visible row after one two-row wheel step.
        click(fd, col=0, row=7)
        send(fd, "four")
        wait_for(fd, screen, "four")

        wheel(fd, down=True, col=0, row=3)
        wait_for(fd, screen, "Field 5")
        click(fd, col=0, row=7)
        send(fd, "five")
        wait_for(fd, screen, "five")

        wheel(fd, down=False, col=0, row=3)
        wait_for(fd, screen, "Field 2")

        send(fd, "\x03")
        status = wait_exit(pid, fd, screen, timeout=2.0)
        if status is None:
            raise AssertionError("Cooper scrolling form did not exit after Ctrl+C")
        assert status == 0, f"exit status {status}"

        print("✓ Cooper scrolling form smoke test passed")
    finally:
        cleanup(fd, pid)


def wheel(fd, down, col, row):
    button = 65 if down else 64
    send(fd, f"\x1b[<{button};{col + 1};{row + 1}M")


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
