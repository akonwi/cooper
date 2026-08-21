#!/usr/bin/env python3
"""Smoke test for the OpenTUI-style retained application prototype."""

import os
import signal
import sys

os.environ.setdefault("ARD", "ard-dev")

from test_harness import Screen, build, send, spawn, wait_exit, wait_for

ROOT = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(ROOT, "retained")


def main():
    build("retained")
    pid, fd = spawn(BIN, rows=8, cols=60)
    screen = Screen(8, 60)
    try:
        wait_for(fd, screen, "Hello from retained Cooper")
        send(fd, "\x03")
        status = wait_exit(pid, fd, screen, timeout=2.0)
        if status is None:
            raise AssertionError("retained Cooper app did not exit after Ctrl+C")
        assert status == 0, f"exit status {status}"
        print("✓ Cooper retained app smoke test passed")
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
