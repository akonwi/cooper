#!/usr/bin/env python3
"""PTY validation for Cooper's built-in Selects and app-local sliders."""

import os
import signal
import sys

from test_harness import Screen, binary_path, build, drain, resize, send, spawn, wait_exit, wait_for

ROOT = os.path.dirname(os.path.abspath(__file__))
BIN = binary_path("widgets")


def sgr(fd, code, col, row, final="M"):
    send(fd, f"\x1b[<{code};{col + 1};{row + 1}{final}")


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
    build("widgets")
    pid, fd = spawn(BIN, rows=24, cols=100)
    screen = Screen(24, 100)
    try:
        wait_for(fd, screen, "WIDGET LAB — built-in Selects + app-local sliders")
        wait_for(fd, screen, "Highlighted: Home (home) - Index: 0")
        drain(fd, screen, 0.15)

        initial = screen.text()
        for expected in (
            "F1 TAB SELECT",
            "F2 SELECT",
            "F3 SLIDERS",
            "TAB SELECT",
            "Profile",
            "Welcome to the home page",
            "Tab selector is FOCUSED",
        ):
            assert expected in initial, f"missing widget-lab specimen {expected!r}"

        # TabSelect keeps highlight and activation separate, exposes all source
        # feature toggles, and scrolls/wraps its twelve fixed-width tabs.
        send(fd, "\x1b[C")
        wait_for(fd, screen, "Highlighted: Profile (profile) - Index: 1")
        send(fd, "\r")
        wait_for(fd, screen, "Last Selected: Profile (profile)")
        send(fd, "u")
        wait_for(fd, screen, "Underline: off")
        send(fd, "p")
        wait_for(fd, screen, "Descriptions hidden — press P")
        send(fd, "s")
        wait_for(fd, screen, "TAB SELECT toggled scroll arrows")
        send(fd, "w")
        wait_for(fd, screen, "Wrap: on")
        send(fd, "\x1b[D")
        send(fd, "\x1b[D")
        wait_for(fd, screen, "Highlighted: API (api) - Index: 11")

        # The shell tabs are mouse-operable. Select uses a compact trigger and
        # anchored menu with mouse activation and fast keyboard navigation.
        click(fd, col=25, row=1)
        wait_for(fd, screen, "SELECT · Compact input with anchored option menu")
        wait_for(fd, screen, "Selection: Home (home) - Index: 0")
        click(fd, col=10, row=6)
        wait_for(fd, screen, "Navigate to the home page")
        click(fd, col=10, row=7)
        wait_for(fd, screen, "SELECT activated Home")
        click(fd, col=10, row=6)
        wheel_down(fd, col=10, row=8)
        send(fd, "\x1b[B")
        wait_for(fd, screen, "Selection: Profile (profile) - Index: 1")
        assert "▶ Profile" in screen.text(), "wheel navigation detached viewport from highlight"
        send(fd, "\x1b[1;2B")
        wait_for(fd, screen, "Selection: Users (users) - Index: 6")
        send(fd, "\r")
        wait_for(fd, screen, "*** ACTIVATED: Users (users) ***")
        send(fd, "d")
        wait_for(fd, screen, "Description: off")
        send(fd, "s")
        wait_for(fd, screen, "Indicator: off")

        # F3 switches to the slider gallery. Mouse drag updates a horizontal
        # slider; number focus and arrows update a vertical slider; reset is
        # independent from the two continuously animated specimens.
        send(fd, "\x1bOR")
        wait_for(fd, screen, "Focused H1 · Value 25")
        drain(fd, screen, 0.15)
        before_lines = screen.text().splitlines()
        h3_row = next(index for index, line in enumerate(before_lines) if "H3 - animated" in line)
        animated_before = before_lines[h3_row + 1]
        drain(fd, screen, 0.4)
        after_lines = screen.text().splitlines()
        h3_row = next(index for index, line in enumerate(after_lines) if "H3 - animated" in line)
        assert after_lines[h3_row + 1] != animated_before, "animated slider dispatch did not repaint"
        drag(fd, start_col=10, start_row=7, end_col=40, end_row=7)
        wait_for(fd, screen, "Focused H1 · Value 40")
        send(fd, "4")
        wait_for(fd, screen, "Focused V1 · Value 0")
        send(fd, "\x1b[A")
        wait_for(fd, screen, "Focused V1 · Value 1")
        send(fd, "r")
        wait_for(fd, screen, "*** All sliders reset to default values ***")
        drain(fd, screen, 0.1)
        assert "│ 25" in screen.text() and "│0" in screen.text(), "slider reset did not restore static defaults"

        # Page controls stay mounted: returning to F1 restores tab state rather
        # than rebuilding the composition.
        click(fd, col=5, row=1)
        wait_for(fd, screen, "Highlighted: API (api) - Index: 11")
        drain(fd, screen, 0.2)
        assert "Underline: off" in screen.text() and "Wrap: on" in screen.text()

        resize(fd, rows=20, cols=70)
        narrow = Screen(20, 70)
        wait_for(fd, narrow, "WIDGET LAB")
        wait_for(fd, narrow, "Highlighted: API (api) - Index: 11")
        drain(fd, narrow, 0.15)
        bottom = next(line for line in narrow.text().splitlines() if line.startswith("└"))
        assert bottom.count("└") == 2 and bottom.endswith("┘"), "compact widget panels lost their borders"

        send(fd, "\x1bOQ")
        wait_for(fd, narrow, "Selection: Users (users)")
        wait_for(fd, narrow, "Index: 6")
        wait_for(fd, narrow, "Users")
        send(fd, "\x1bOR")
        wait_for(fd, narrow, "Focused H1 · Value 25")
        wait_for(fd, narrow, "H2 - 3h×48w")

        send(fd, "\x03")
        status = wait_exit(pid, fd, narrow, timeout=2.0)
        if status is None:
            raise AssertionError("widget lab did not exit after Ctrl+C")
        assert status == 0, f"exit status {status}"

        print("✓ Cooper built-in Select widget lab PTY test passed")
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
