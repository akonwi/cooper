#!/usr/bin/env python3
"""End-to-end PTY validation for Cooper's Interaction Lab."""

import os
import signal
import sys

os.environ.setdefault("ARD", "ard-dev")

from test_harness import Screen, build, read_for, send, spawn, wait_exit, wait_for

ROOT = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(ROOT, "interaction_lab")


def sgr(fd, code, col, row, final="M"):
    send(fd, f"\x1b[<{code};{col + 1};{row + 1}{final}")


def click(fd, col, row, code=0):
    sgr(fd, code, col, row)
    sgr(fd, code, col, row, "m")


def drag(fd, start_col, start_row, end_col, end_row, button=0):
    sgr(fd, button, start_col, start_row)
    sgr(fd, 32 | button, end_col, end_row)
    sgr(fd, button, end_col, end_row, "m")


def move(fd, col, row):
    sgr(fd, 35, col, row)


def main():
    os.chdir(ROOT)
    build("interaction_lab")
    pid, fd = spawn(BIN, rows=24, cols=100)
    screen = Screen(24, 100)
    try:
        wait_for(fd, screen, "last: ready")

        # Terminal focus is independent from Cooper's focused control.
        send(fd, "\x1b[O")
        wait_for(fd, screen, "Window focus: UNFOCUSED")
        assert "focus: none" in screen.text()
        send(fd, "\x1b[I")
        wait_for(fd, screen, "Window focus: FOCUSED")
        assert "focus: none" in screen.text()

        # The hit is a nested child, but autofocus walks to its bordered ancestor.
        click(fd, col=10, row=3)
        wait_for(fd, screen, "focus: ancestor")

        # FRONT overlaps BACK and wins through z-index ordering.
        click(fd, col=32, row=6)
        wait_for(fd, screen, "stack: FRONT")

        # Right drag remains hit-routed and never synthesizes drop.
        drag(fd, start_col=1, start_row=9, end_col=43, end_row=9, button=2)
        wait_for(fd, screen, "right drag hit-routed")

        # SOURCE follows the captured left drag, while the higher drop target
        # remains the physical release target beneath it.
        drag(fd, start_col=1, start_row=9, end_col=43, end_row=9)
        wait_for(fd, screen, "drag: dropped in zone")
        click(fd, col=43, row=9)
        wait_for(fd, screen, "drag: click only")

        # Move onto LEFT, then use the visible m instruction to change layout
        # without another mouse sequence.
        move(fd, col=1, row=14)
        wait_for(fd, screen, "hover: LEFT ✓")
        send(fd, "m")
        wait_for(fd, screen, "last: m swapped hover tile layout")
        wait_for(fd, screen, "hover: RIGHT ✓")

        # Double-click selects one complete unlinked read-only word without
        # invoking the linked SELECTABLE prefix during the PTY suite.
        click(fd, col=32, row=16)
        click(fd, col=32, row=16)
        wait_for(fd, screen, "selection: Alpha")

        # Select across the wrapped/read-only Text and extend with Ctrl+click.
        drag(fd, start_col=0, start_row=16, end_col=10, end_row=17)
        wait_for(fd, screen, "selection: SELECTABLE")
        click(fd, col=20, row=17, code=16)
        wait_for(fd, screen, "Second line")

        # Select and replace a range in the horizontally panned Input.
        drag(fd, start_col=17, start_row=19, end_col=21, end_row=19)
        wait_for(fd, screen, "selection: art")
        send(fd, "X")
        wait_for(fd, screen, "last: Input changed")
        wait_for(fd, screen, "selection: none")
        send(fd, "m")
        wait_for(fd, screen, "select pXmof")

        # Wheel translation changes paint and selection coordinates inside the
        # visibly bordered scroll viewport.
        sgr(fd, 65, col=1, row=21)
        for _ in range(8):
            read_for(fd, screen, 0.05)
        assert screen.line(21).startswith("│scroll row 3"), "wheel did not translate visible rows"
        drag(fd, start_col=1, start_row=21, end_col=11, end_row=22)
        wait_for(fd, screen, "selection: scroll row")

        send(fd, "\x03")
        status = wait_exit(pid, fd, screen, timeout=2.0)
        if status is None:
            raise AssertionError("Interaction Lab did not exit after Ctrl+C")
        assert status == 0, f"exit status {status}"
        test_focus_without_mouse()
        print("✓ Cooper Interaction Lab PTY test passed")
    finally:
        cleanup(fd, pid)


def test_focus_without_mouse():
    build("terminal_focus")
    pid, fd = spawn(os.path.join(ROOT, "terminal_focus"), rows=3, cols=40)
    screen = Screen(3, 40)
    try:
        wait_for(fd, screen, "terminal: unknown")
        send(fd, "\x1b[O")
        wait_for(fd, screen, "terminal: blurred")
        send(fd, "\x1b[I")
        wait_for(fd, screen, "terminal: focused")
        send(fd, "\x03")
        status = wait_exit(pid, fd, screen, timeout=2.0)
        if status is None:
            raise AssertionError("mouse-disabled focus probe did not exit")
        assert status == 0, f"focus probe exit status {status}"
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
