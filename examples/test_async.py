#!/usr/bin/env python3
"""Smoke test for App-lifetime cancellation and async UI dispatch."""

import os
import signal
import sys

from test_harness import Screen, binary_path, build, send, spawn, wait_exit, wait_for

ROOT = os.path.dirname(os.path.abspath(__file__))
BIN = binary_path("async")
PRE_RUN_DESTROY_BIN = binary_path("pre_run_destroy")


def run_pre_run_destroy():
    pid, fd = spawn(PRE_RUN_DESTROY_BIN, rows=4, cols=60)
    screen = Screen(4, 60)
    try:
        status = wait_exit(pid, fd, screen, timeout=2.0)
        if status is None:
            raise AssertionError("pre-run App.destroy did not exit")
        assert status == 0, f"pre-run destroy exit status {status}"
    finally:
        cleanup(fd, pid)


def run_cancelled_work():
    pid, fd = spawn(BIN, rows=4, cols=60)
    screen = Screen(4, 60)
    try:
        wait_for(fd, screen, "Loading asynchronously")
        send(fd, "\x03")
        status = wait_exit(pid, fd, screen, timeout=2.0)
        if status is None:
            raise AssertionError("async app did not exit while App work was pending")
        assert status == 0, f"cancelled-work exit status {status}"
    finally:
        cleanup(fd, pid)


def run_completed_work():
    pid, fd = spawn(BIN, rows=4, cols=60)
    screen = Screen(4, 60)
    try:
        wait_for(fd, screen, "Loading asynchronously")
        wait_for(fd, screen, "Loaded on the UI thread")
        status = wait_exit(pid, fd, screen, timeout=2.0)
        if status is None:
            raise AssertionError("async app did not exit after App.destroy")
        assert status == 0, f"completed-mount exit status {status}"
    finally:
        cleanup(fd, pid)


def main():
    build("async", source="fixtures/async.ard")
    build("pre_run_destroy", source="fixtures/pre_run_destroy.ard")
    run_pre_run_destroy()
    run_cancelled_work()
    run_completed_work()
    print("✓ Cooper App-lifetime async smoke test passed")


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
