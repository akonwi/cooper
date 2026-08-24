#!/usr/bin/env python3
"""PTY validation for Cooper's OpenTUI-inspired mouse interaction demo."""

import os
import signal
import sys

from test_harness import Screen, binary_path, build, drain, resize, send, spawn, wait_exit, wait_for

ROOT = os.path.dirname(os.path.abspath(__file__))
BIN = binary_path("event_inspector")


def sgr(fd, code, col, row, final="M"):
    send(fd, f"\x1b[<{code};{col + 1};{row + 1}{final}")


def move(fd, col, row):
    sgr(fd, 35, col, row)


def click(fd, col, row):
    sgr(fd, 0, col, row)
    sgr(fd, 0, col, row, "m")


def drag(fd, start_col, start_row, end_col, end_row):
    sgr(fd, 0, start_col, start_row)
    sgr(fd, 32, end_col, end_row)
    sgr(fd, 0, end_col, end_row, "m")


def wheel(fd, col, row, down=True):
    sgr(fd, 65 if down else 64, col, row)


def main():
    os.chdir(ROOT)
    build("event_inspector")
    pid, fd = spawn(BIN, rows=24, cols=100)
    screen = Screen(24, 100)
    try:
        wait_for(fd, screen, "MOUSE INTERACTION DEMO")
        wait_for(fd, screen, "ready · trails 0/32 · cells 0")
        drain(fd, screen, 0.15)

        initial = screen.text()
        for expected in (
            "DRAGGABLE OBJECTS",
            "BOX 1",
            "BOX 2",
            "BOX 3",
            "BOX 4 · O HIDD",
            "drag me",
            "This should be cu",
            "Move: cyan trail",
            "Drag: orange trail",
            "Click empty cells: pink",
        ):
            assert expected in initial, f"missing mouse-demo specimen {expected!r}"
        overflow_line = next(line for line in initial.splitlines() if "This should be cu" in line)
        assert "right" not in overflow_line, "overflow-hidden card failed to clip its long child"

        # Movement over the stage leaves retained cyan trail marks. The fixed
        # ring caps at 32 markers instead of allocating on every mouse event.
        for index in range(40):
            move(fd, col=58 + index % 8, row=8 + index % 4)
        wait_for(fd, screen, "trails 32/32")
        drain(fd, screen, 0.1)
        assert screen.line(11)[65] == "+", "latest trail cell did not paint the live cursor"

        # Empty-cell clicks toggle the pink activation layer without affecting
        # draggable card input.
        click(fd, col=60, row=8)
        wait_for(fd, screen, "cell on at 59,2")
        drain(fd, screen, 0.1)
        assert "cells 1" in screen.text() and screen.line(8)[60] == "█"
        click(fd, col=60, row=8)
        wait_for(fd, screen, "cell off at 59,2")
        drain(fd, screen, 0.1)
        assert "cells 0" in screen.text() and screen.line(8)[60] != "█"

        # An ordinary card click raises the retained object. Scrolling at its
        # overlap with BOX 2 then hit-tests the newly raised BOX 1.
        click(fd, col=8, row=9)
        wait_for(fd, screen, "BOX 1 clicked")
        assert "clicked" in screen.text()
        wheel(fd, col=20, row=10, down=True)
        wait_for(fd, screen, "BOX 1 scroll down")
        assert "scroll down" in screen.text()

        # Reset restores original absolute positions before testing capture and
        # release over another retained box.
        send(fd, "r")
        wait_for(fd, screen, "scene reset · trails 0/32 · cells 0")
        drag(fd, start_col=8, start_row=9, end_col=25, end_row=11)
        wait_for(fd, screen, "BOX 1 dropped on BOX 2")
        drain(fd, screen, 0.15)
        dropped = screen.text()
        assert "got BOX 1" in dropped, "drop target did not show source feedback"
        assert "trails 1/32" in dropped, "captured drag did not leave an orange trail"
        move(fd, col=60, row=8)
        drain(fd, screen, 0.1)
        assert "BOX 1 dropped on BOX 2" in screen.text() and "got BOX 1" in screen.text(), "drop feedback did not remain latched"

        # Clear affects marks without resetting card layout or drop feedback;
        # reset restores exact home geometry and default labels.
        send(fd, "c")
        wait_for(fd, screen, "trails and cells cleared · trails 0/32 · cells 0")
        assert "got BOX 1" in screen.text(), "clear unexpectedly reset card state"
        send(fd, "r")
        wait_for(fd, screen, "scene reset")
        drain(fd, screen, 0.1)
        assert "got BOX 1" not in screen.text() and "BOX 1" in screen.line(7)

        # Move BOX 3 beyond a future narrow viewport, then prove resize clips
        # the retained offscreen card and marker paint inside the stage border.
        drag(fd, start_col=40, start_row=12, end_col=90, end_row=10)
        wait_for(fd, screen, "BOX 3 released")
        resize(fd, rows=24, cols=70)
        narrow = Screen(24, 70)
        wait_for(fd, narrow, "MOUSE INTERACTION DEMO")
        wait_for(fd, narrow, "BOX 3 released")
        drain(fd, narrow, 0.2)
        stage_bottom = next(line for line in narrow.text().splitlines() if line.startswith("╰"))
        assert stage_bottom.endswith("╯"), "mouse-demo content overwrote the narrow stage border"
        assert narrow.line(23).endswith("┘"), "mouse-demo footer overwrote its border"

        send(fd, "\x03")
        status = wait_exit(pid, fd, narrow, timeout=2.0)
        if status is None:
            raise AssertionError("mouse interaction demo did not exit after Ctrl+C")
        assert status == 0, f"exit status {status}"

        print("✓ Cooper OpenTUI-style mouse interaction PTY test passed")
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
