#!/usr/bin/env python3
"""Smoke test for the retained filesystem explorer vertical slice."""

import os
import signal
import sys

os.environ.setdefault("ARD", "ard-dev")

from test_harness import (
    Screen,
    build,
    read_for,
    resize,
    send,
    spawn,
    wait_exit,
    wait_for,
)

ROOT = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(ROOT, "explorer")


def click(fd, col, row):
    send(fd, f"\x1b[<0;{col + 1};{row + 1}M")


def wheel_down(fd, col, row):
    send(fd, f"\x1b[<65;{col + 1};{row + 1}M")


def main():
    os.chdir(ROOT)
    build("explorer")
    pid, fd = spawn(BIN, rows=8, cols=90)
    screen = Screen(8, 90)
    try:
        wait_for(fd, screen, "Retained Explorer")
        wait_for(fd, screen, "ard.toml")

        wide_details = screen.line(4).find("Details")
        assert wide_details >= 40, "details pane was not horizontally positioned"
        first_label = screen.line(4)[:wide_details].lstrip("> ").rstrip()
        second_label = screen.line(5)[:wide_details].lstrip("> ").rstrip()
        assert first_label and second_label, "explorer did not expose two retained rows"

        # Initial focus belongs to Input; Tab traverses to the first persistent row.
        send(fd, "\t")
        send(fd, "\r")
        wait_for(fd, screen, f"Selected: {first_label}")

        # Mouse targeting uses the retained row geometry directly.
        click(fd, col=2, row=5)
        wait_for(fd, screen, f"Selected: {second_label}")
        resize(fd, rows=8, cols=60)
        for _ in range(5):
            read_for(fd, screen, 0.1)
        narrow_details = screen.line(4).find("Details")
        assert 25 <= narrow_details < wide_details, "panes did not respond to terminal resize"

        # Wheel translation changes both paint and hit coordinates. Activate the
        # row now occupying the second visible list line.
        wheel_down(fd, col=2, row=4)
        for _ in range(5):
            read_for(fd, screen, 0.1)
        visible_label = screen.line(5)[:narrow_details].lstrip("> ").rstrip()
        assert visible_label, "scroll did not expose another retained row"
        click(fd, col=2, row=5)
        wait_for(fd, screen, f"Selected: {visible_label}")

        send(fd, "\x03")
        status = wait_exit(pid, fd, screen, timeout=2.0)
        if status is None:
            raise AssertionError("explorer did not exit after Ctrl+C")
        assert status == 0, f"exit status {status}"
        print("✓ Cooper explorer smoke test passed")
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
