#!/usr/bin/env python3
"""PTY validation for Cooper's demand-driven animation frame scheduler."""

import os
import re
import signal
import sys
import time

from test_harness import Screen, binary_path, build, drain, read_for, send, spawn, wait_exit, wait_for

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



def run_spring_lab():
    build("spring_lab")
    pid, fd = spawn(binary_path("spring_lab"), rows=24, cols=80)
    screen = Screen(24, 80)
    rows = list(range(4, 22, 3))
    try:
        wait_for(fd, screen, "FAST")
        deadline = time.monotonic() + 3.0
        fractional = False
        while time.monotonic() < deadline:
            read_for(fd, screen, 0.01)
            fractional |= any(char in screen.text() for char in "▏▎▍▌▋▊▉")
            assert screen.line(11).find("●") <= 48, "critical spring must not overshoot from rest"
            assert screen.line(14).find("●") <= 48, "heavy damping must not overshoot from rest"
            if screen.line(5).find("●") > 48:
                break
        assert screen.line(5).find("●") > 48, "bouncy lane must visibly overshoot"
        assert fractional, "fill bars must expose fractional-cell motion"
        positions = [screen.line(row + 1).find("●") for row in rows]
        assert len(set(positions)) >= 3, "presets must show distinct responses to the same target"
        send(fd, " ")
        wait_for(fd, screen, "PAUSED target=46")
        frozen = screen.text()
        drain(fd, screen, 0.3)
        assert screen.text() == frozen, "pause must freeze every lane and elapsed time"
        send(fd, " ")
        wait_for(fd, screen, "COMPARE target=46")
        send(fd, "c")
        wait_for(fd, screen, "COMPARE target=32")
        for row in rows:
            assert screen.line(row + 1)[34] in "│●", "target guides must move together"
        deadline = time.monotonic() + 12.0
        while screen.text().count("SETTLED") != 6 and time.monotonic() < deadline:
            read_for(fd, screen)
        assert screen.text().count("SETTLED") == 6, "every preset must settle"
        for row in rows:
            assert screen.line(row + 1).find("●") == 34, "all markers must settle at the center target"
            assert screen.line(row + 2).strip() == "█" * 32, "fill must match the exact settled position"
            assert "x=32.00 v=0.00" in screen.line(row), "telemetry must show exact rest"
        frozen = screen.text()
        drain(fd, screen, 0.2)
        assert screen.text() == frozen, "settled springs must stop updating"
        send(fd, "\x1b[C")
        wait_for(fd, screen, "COMPARE target=46")
        wait_for(fd, screen, "MOVING")
        stop(pid, fd, screen, "spring lab")
    finally:
        cleanup(fd, pid)


def main():
    os.chdir(ROOT)
    run_animation()
    run_suspension()
    run_spring_lab()
    print("✓ Cooper animation PTY tests passed")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"FAIL: {error}", file=sys.stderr)
        sys.exit(1)
