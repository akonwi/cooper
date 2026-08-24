#!/usr/bin/env python3
"""PTY validation for Cooper's interactive layout playground."""

import os
import signal
import sys

from test_harness import Screen, binary_path, build, drain, resize, send, spawn, wait_exit, wait_for

ROOT = os.path.dirname(os.path.abspath(__file__))
BIN = binary_path("layout_playground")


def label_row(screen, label):
    for index, line in enumerate(screen.text().splitlines()):
        if label in line:
            return index
    raise AssertionError(f"did not find card label {label!r}\n{screen.text()}")


def select(fd, screen, key, status):
    send(fd, key)
    wait_for(fd, screen, status)
    drain(fd, screen, 0.15)


def main():
    os.chdir(ROOT)
    build("layout_playground")
    pid, fd = spawn(BIN, rows=24, cols=80)
    screen = Screen(24, 80)
    try:
        wait_for(fd, screen, "Preset 1/7")
        drain(fd, screen, 0.2)

        # Horizontal flow keeps all retained cards on one row.
        horizontal_rows = [label_row(screen, name) for name in ("ALPHA", "BRAVO", "CHARLIE", "DELTA")]
        assert len(set(horizontal_rows)) == 1, f"cards did not share a row: {horizontal_rows}"
        wide_delta_column = screen.line(horizontal_rows[0]).index("DELTA")

        # The same controls become a top-to-bottom stack.
        select(fd, screen, "2", "Preset 2/7")
        vertical_rows = [label_row(screen, name) for name in ("ALPHA", "BRAVO", "CHARLIE", "DELTA")]
        assert vertical_rows == sorted(vertical_rows), f"cards were not vertically ordered: {vertical_rows}"
        assert len(set(vertical_rows)) == 4, f"vertical cards shared rows: {vertical_rows}"

        # Wrapping lays out two cards per line without rebuilding the tree.
        select(fd, screen, "3", "Preset 3/7")
        alpha = label_row(screen, "ALPHA")
        bravo = label_row(screen, "BRAVO")
        charlie = label_row(screen, "CHARLIE")
        delta = label_row(screen, "DELTA")
        assert alpha == bravo, "first wrapped pair did not share a row"
        assert charlie == delta, "second wrapped pair did not share a row"
        assert alpha < charlie, "wrapped rows appeared out of order"

        # Number keys reach every remaining complete Style configuration.
        select(fd, screen, "4", "Preset 4/7")
        centered_row = label_row(screen, "ALPHA")
        centered_line = screen.line(centered_row)
        centered_alpha = centered_line.index("ALPHA")
        centered_delta = centered_line.index("DELTA")

        select(fd, screen, "5", "Preset 5/7")
        spaced_row = label_row(screen, "ALPHA")
        spaced_line = screen.line(spaced_row)
        assert spaced_line.index("ALPHA") < centered_alpha, "space-between did not move the first card outward"
        assert spaced_line.index("DELTA") > centered_delta, "space-between did not move the last card outward"
        select(fd, screen, "6", "Preset 6/7")
        reversed_rows = [label_row(screen, name) for name in ("ALPHA", "BRAVO", "CHARLIE", "DELTA")]
        assert len(set(reversed_rows)) == 1, "reversed cards did not share a row"
        reversed_line = screen.line(reversed_rows[0])
        assert reversed_line.index("DELTA") < reversed_line.index("ALPHA"), "row-reverse did not reverse paint order"

        select(fd, screen, "7", "Preset 7/7")
        assert "ABSOLUTE OVERLAY" in screen.text()
        assert "ALPHA" in screen.text(), "earlier card with the highest z-index was obscured"

        # Space cycles and wraps from the seventh preset back to the first.
        select(fd, screen, " ", "Preset 1/7")

        # A terminal resize drives a new layout without application-side resize code.
        resize(fd, rows=24, cols=60)
        narrow = Screen(24, 60)
        wait_for(fd, narrow, "Preset 1/7")
        drain(fd, narrow, 0.2)
        narrow_rows = [label_row(narrow, name) for name in ("ALPHA", "BRAVO", "CHARLIE", "DELTA")]
        assert len(set(narrow_rows)) == 1, f"cards did not reflow after resize: {narrow_rows}"
        narrow_delta_column = narrow.line(narrow_rows[0]).index("DELTA")
        assert narrow_delta_column < wide_delta_column, "horizontal cards did not contract after resize"
        assert narrow.line(23).endswith("┘"), "single-line footer overwrote its border after resize"

        send(fd, "q")
        status = wait_exit(pid, fd, narrow, timeout=2.0)
        if status is None:
            raise AssertionError("layout playground did not exit after Q")
        assert status == 0, f"exit status {status}"

        print("✓ Cooper layout playground PTY test passed")
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
