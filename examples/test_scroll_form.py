#!/usr/bin/env python3
"""Smoke test for Cooper's multi-child vertical ScrollBox."""

import os
import signal
import sys

from test_harness import Screen, binary_path, build, drain, resize, send, spawn, wait_exit, wait_for

ROOT = os.path.dirname(os.path.abspath(__file__))
BIN = binary_path("scroll_form")


def main():
    build("scroll_form", source="fixtures/scroll_form.ard")
    pid, fd = spawn(BIN, rows=8, cols=60)
    screen = Screen(8, 60)
    try:
        wait_for(fd, screen, "Scrollable retained form")
        wait_for(fd, screen, "Field 3")
        assert screen.line(1).endswith("┃"), screen.text()

        # Focus traversal reveals a direct ScrollBox child at the viewport bottom.
        send(fd, "\t")
        send(fd, "\t")
        send(fd, "\t")
        drain(fd, screen)
        assert screen.line(6).startswith("Field 4"), screen.text()
        assert screen.line(7).startswith("value 4"), screen.text()

        # Resize recomputes layout and keeps the focused descendant visible.
        resize(fd, rows=6, cols=60)
        drain(fd, screen)
        assert screen.line(4).startswith("Field 4"), screen.text()
        assert screen.line(5).startswith("value 4"), screen.text()
        resize(fd, rows=8, cols=60)
        drain(fd, screen)

        send(fd, "four")
        wait_for(fd, screen, "four")

        # Wheel movement preserves manual scroll, and clicking translated
        # geometry focuses the visible fifth Input.
        wheel(fd, down=True, col=0, row=3)
        wait_for(fd, screen, "Field 6")
        click(fd, col=0, row=4)
        send(fd, "three")
        wait_for(fd, screen, "three")

        # The built-in proportional thumb accepts captured terminal mouse drag.
        drag(fd, start_col=59, start_row=2, end_col=59, end_row=7)
        wait_for(fd, screen, "Field 8")
        assert screen.line(7).startswith("value 8"), screen.text()
        assert screen.line(7).endswith("┃"), screen.text()

        send(fd, "\x03")
        status = wait_exit(pid, fd, screen, timeout=2.0)
        if status is None:
            raise AssertionError("Cooper scrolling form did not exit after Ctrl+C")
        assert status == 0, f"exit status {status}"
        print("✓ Cooper scrolling form smoke test passed")
    finally:
        cleanup(fd, pid)


def sgr(fd, code, col, row, suffix="M"):
    send(fd, f"\x1b[<{code};{col + 1};{row + 1}{suffix}")


def drag(fd, start_col, start_row, end_col, end_row):
    sgr(fd, 0, start_col, start_row)
    sgr(fd, 32, end_col, end_row)
    sgr(fd, 0, end_col, end_row, "m")


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
