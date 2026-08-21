#!/usr/bin/env python3
"""Smoke test for attachment-scoped async UI dispatch."""

import os
import signal
import sys

from test_harness import Screen, build, send, spawn, wait_exit, wait_for

ROOT = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(ROOT, "async")


def run_cancelled_mount():
    pid, fd = spawn(BIN, rows=4, cols=60)
    screen = Screen(4, 60)
    try:
        wait_for(fd, screen, "Loading asynchronously")
        send(fd, "\x03")
        status = wait_exit(pid, fd, screen, timeout=2.0)
        if status is None:
            raise AssertionError("async app did not exit while mount work was pending")
        assert status == 0, f"cancelled-mount exit status {status}"
    finally:
        cleanup(fd, pid)


def run_completed_mount():
    pid, fd = spawn(BIN, rows=4, cols=60)
    screen = Screen(4, 60)
    try:
        wait_for(fd, screen, "Loading asynchronously")
        wait_for(fd, screen, "Loaded on the UI thread")
        send(fd, "\x03")
        status = wait_exit(pid, fd, screen, timeout=2.0)
        if status is None:
            raise AssertionError("async app did not exit after Ctrl+C")
        assert status == 0, f"completed-mount exit status {status}"
    finally:
        cleanup(fd, pid)


def main():
    build("async")
    run_cancelled_mount()
    run_completed_mount()
    print("✓ Cooper attachment-scoped async smoke test passed")


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
