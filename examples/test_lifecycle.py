#!/usr/bin/env python3
"""PTY validation for reusable App startup, suspension, resume, and teardown."""

import os
import signal
import sys
import time

from test_harness import Screen, binary_path, build, read_for, spawn

ROOT = os.path.dirname(os.path.abspath(__file__))
BIN = binary_path("lifecycle")
PRE_START_SIGNAL_BIN = binary_path("pre_start_signal")


def main():
    os.chdir(ROOT)
    build("lifecycle", source="fixtures/lifecycle.ard")
    build("pre_start_signal", source="fixtures/pre_start_signal.ard")
    pid, fd = spawn(BIN, rows=4, cols=40)
    screen = Screen(4, 40)
    output = bytearray()
    seen_ready = False
    seen_resumed = False
    status = None
    try:
        deadline = time.time() + 4.0
        while time.time() < deadline:
            output.extend(read_for(fd, screen, 0.03))
            visible = screen.text()
            seen_ready = seen_ready or "READY" in visible
            seen_resumed = seen_resumed or "RESUMED" in visible
            done, current = os.waitpid(pid, os.WNOHANG)
            if done == pid:
                status = current
                break

        if status is None:
            raise AssertionError("lifecycle example did not exit")
        assert status == 0, f"lifecycle exit status {status}"
        assert seen_ready, "nonblocking start did not commit the initial frame"
        assert seen_resumed, "resume did not repaint the retained tree"
        assert b"\x1b[?1049l" in output, "suspend did not leave the alternate screen"
        assert output.count(b"\x1b[?1049h") >= 2, "resume did not re-enter the alternate screen"
        test_signal_shutdown()
        test_pre_start_signal_shutdown()
        print("✓ Cooper reusable lifecycle PTY test passed")
    finally:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass


def test_pre_start_signal_shutdown():
    pid, fd = spawn(PRE_START_SIGNAL_BIN, rows=4, cols=40)
    screen = Screen(4, 40)
    output = bytearray()
    try:
        deadline = time.time() + 1.0
        while time.time() < deadline and b"\x1b[?1049h" not in output:
            output.extend(read_for(fd, screen, 0.03))
        assert b"\x1b[?1049h" in output, "pre-start signal probe did not acquire the terminal"

        os.kill(pid, signal.SIGTERM)
        status = None
        deadline = time.time() + 2.0
        while time.time() < deadline:
            output.extend(read_for(fd, screen, 0.03))
            done, current = os.waitpid(pid, os.WNOHANG)
            if done == pid:
                status = current
                break
        assert status == 0, f"pre-start signal shutdown exit status {status}"
        assert b"\x1b[?1049l" in output, "pre-start signal did not restore the terminal"
    finally:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass


def test_signal_shutdown():
    pid, fd = spawn(BIN, rows=4, cols=40)
    screen = Screen(4, 40)
    output = bytearray()
    try:
        deadline = time.time() + 2.0
        while time.time() < deadline and "READY" not in screen.text():
            output.extend(read_for(fd, screen, 0.03))
        assert "READY" in screen.text(), "signal lifecycle probe did not start"

        os.kill(pid, signal.SIGTERM)
        status = None
        deadline = time.time() + 2.0
        while time.time() < deadline:
            output.extend(read_for(fd, screen, 0.03))
            done, current = os.waitpid(pid, os.WNOHANG)
            if done == pid:
                status = current
                break
        assert status == 0, f"signal shutdown exit status {status}"
        assert b"\x1b[?1049l" in output, "signal shutdown did not restore the terminal"
    finally:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"FAIL: {err}", file=sys.stderr)
        sys.exit(1)
