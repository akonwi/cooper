#!/usr/bin/env python3
"""PTY validation for Cooper's nested stacking-context demo."""

import os
import signal
import sys

from test_harness import Screen, binary_path, build, drain, resize, send, spawn, wait_exit, wait_for

ROOT = os.path.dirname(os.path.abspath(__file__))
BIN = binary_path("stacking")


def click(fd, col, row):
    send(fd, f"\x1b[<0;{col + 1};{row + 1}M")
    send(fd, f"\x1b[<0;{col + 1};{row + 1}m")


def main():
    os.chdir(ROOT)
    build("stacking")
    pid, fd = spawn(BIN, rows=24, cols=90)
    screen = Screen(24, 90)
    try:
        wait_for(fd, screen, "Active: CHARLIE")
        drain(fd, screen, 0.15)

        initial = screen.text()
        for expected in (
            "COOPER STACKING CONTEXTS",
            "ALPHA",
            "BRAVO",
            "CHARLIE",
            "STACK INSPECTOR",
            "ALPHA · BRAVO · CHARLIE",
            "99 (inside each parent)",
            "Auto: OFF",
        ):
            assert expected in initial, f"missing stacking specimen {expected!r}"

        # ALPHA's nested z=99 badge occupies this overlap, but initial parent
        # ordering paints and hit-tests CHARLIE above the complete ALPHA subtree.
        assert "z = 99" not in screen.line(13)[18:36], "low-parent child escaped during paint"
        click(fd, col=25, row=12)
        wait_for(fd, screen, "Hit: CHARLIE#1")

        # Raising ALPHA rotates the stable 0..2 parent order. Its nested badge
        # now paints at the overlap and receives the same physical hit.
        send(fd, "1")
        wait_for(fd, screen, "Active: ALPHA · Parent z: 2")
        drain(fd, screen, 0.1)
        assert "BRAVO · CHARLIE · ALPHA" in screen.text()
        assert "z = 99" in screen.line(13)[18:36], "raised nested child did not paint above sibling parents"
        click(fd, col=25, row=12)
        wait_for(fd, screen, "Hit: ALPHA#2")

        # Movement updates the complete absolute Style without rebuilding the
        # layer or disturbing its z-index.
        send(fd, "\x1b[C")
        wait_for(fd, screen, "Position: 3,1")
        send(fd, "\x1b[B")
        wait_for(fd, screen, "Position: 3,2")
        assert "Parent z: 2" in screen.text()

        # Space advances relative to the active layer; reset restores positions,
        # order and the original front layer.
        send(fd, " ")
        wait_for(fd, screen, "Active: BRAVO · Parent z: 2")
        send(fd, "r")
        wait_for(fd, screen, "Active: CHARLIE · Parent z: 2 · Position: 20,4 · Auto: OFF")
        assert "ALPHA · BRAVO · CHARLIE" in screen.text()

        # Clicking an exposed ALPHA edge bubbles from nested content to its
        # group and raises the complete subtree.
        click(fd, col=4, row=8)
        wait_for(fd, screen, "Active: ALPHA · Parent z: 2")

        # Autoplay reads UI-owned state only inside a serialized dispatch.
        send(fd, "a")
        wait_for(fd, screen, "Auto: ON")
        wait_for(fd, screen, "Active: BRAVO", timeout=2.5)
        send(fd, "a")
        wait_for(fd, screen, "Auto: OFF")

        # A narrow terminal clips moving layers inside the scene content instead
        # of allowing them to overwrite either panel border.
        resize(fd, rows=24, cols=70)
        narrow = Screen(24, 70)
        wait_for(fd, narrow, "AUTOPLAY  OFF")
        drain(fd, narrow, 0.2)
        panel_bottom = next(line for line in narrow.text().splitlines() if line.startswith("╰"))
        assert panel_bottom.count("╯") == 2, "stacked content overwrote a panel border"
        assert narrow.line(23).endswith("┘"), "stacking footer overwrote its border"

        send(fd, "q")
        status = wait_exit(pid, fd, narrow, timeout=2.0)
        if status is None:
            raise AssertionError("stacking demo did not exit after Q")
        assert status == 0, f"exit status {status}"

        print("✓ Cooper stacking-context PTY test passed")
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
