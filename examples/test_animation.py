#!/usr/bin/env python3
"""PTY validation for Cooper's demand-driven animation frame scheduler."""

import os
import re
import signal
import sys

from test_harness import Screen, binary_path, build, send, spawn, wait_exit, wait_for

ROOT = os.path.dirname(os.path.abspath(__file__))


def cleanup(fd, pid):
    try:
        os.close(fd)
    except OSError:
        pass
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass


def stop(pid, fd, screen, name):
    send(fd, "\x03")
    status = wait_exit(pid, fd, screen, timeout=2.0)
    if status is None:
        raise AssertionError(f"{name} did not exit after Ctrl+C")
    assert status == 0, f"{name} exit status {status}"


def run_animation():
    build("animation")
    pid, fd = spawn(binary_path("animation"), rows=5, cols=40)
    screen = Screen(5, 40)
    try:
        wait_for(fd, screen, "DONE frames=")
        match = re.search(r"DONE frames=(\d+)", screen.text())
        frames = int(match.group(1)) if match else 0
        assert 2 <= frames <= 200, f"animation frame pacing was outside expected bounds: {screen.text()!r}"
        assert screen.line(0)[20] == "●", "animation did not settle at its final retained position"
        stop(pid, fd, screen, "animation example")
    finally:
        cleanup(fd, pid)


def run_suspension():
    build("animation_suspend", source="fixtures/animation_suspend.ard")
    pid, fd = spawn(binary_path("animation_suspend"), rows=4, cols=40)
    screen = Screen(4, 40)
    try:
        wait_for(fd, screen, "FROZEN")
        wait_for(fd, screen, "DONE")
        stop(pid, fd, screen, "animation suspension fixture")
    finally:
        cleanup(fd, pid)



def main():
    os.chdir(ROOT)
    run_animation()
    run_suspension()
    print("✓ Cooper animation PTY tests passed")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"FAIL: {error}", file=sys.stderr)
        sys.exit(1)
