#!/usr/bin/env python3
"""PTY validation for Cooper's OSC 52 clipboard service."""

import base64
import os
import signal
import sys
import time

from test_harness import Screen, binary_path, build, read_for, send, spawn, wait_exit, wait_for

ROOT = os.path.dirname(os.path.abspath(__file__))
BIN = binary_path("clipboard")


def osc52(payload):
    return b"\x1b]52;c;" + payload + b"\x1b\\"


def wait_for_bytes(fd, screen, needle, timeout=4.0):
    captured = b""
    deadline = time.time() + timeout
    while time.time() < deadline:
        captured += read_for(fd, screen, 0.05)
        if needle in captured:
            return captured
    raise AssertionError(f"did not see terminal bytes {needle!r}; captured {captured!r}")


def main():
    os.chdir(ROOT)
    build("clipboard", source="fixtures/clipboard.ard")
    pid, fd = spawn(BIN, rows=6, cols=80)
    screen = Screen(6, 80)
    try:
        wait_for(fd, screen, "Clipboard fixture ready")

        copied = "Cooper clipboard ✓".encode()
        send(fd, "w")
        wait_for_bytes(fd, screen, osc52(base64.b64encode(copied)))
        wait_for(fd, screen, "WRITE EMITTED")

        send(fd, "c")
        wait_for_bytes(fd, screen, osc52(b""))
        wait_for(fd, screen, "CLEAR EMITTED")

        send(fd, "r")
        wait_for_bytes(fd, screen, osc52(b"?"))
        send(fd, "r")
        wait_for(fd, screen, "READ ERROR: clipboard read already in progress")

        response = base64.b64encode("terminal answer".encode()).decode()
        send(fd, f"\x1b]52;c;{response}\x1b\\")
        wait_for(fd, screen, "READ: terminal answer")

        # OSC 52 responses have no request IDs, so suspension is rejected while
        # a read is pending rather than allowing a stale response after resume.
        send(fd, "r")
        wait_for_bytes(fd, screen, osc52(b"?"))
        send(fd, "s")
        wait_for(fd, screen, "SUSPEND ERROR")
        pending_response = base64.b64encode("pending response".encode()).decode()
        send(fd, f"\x1b]52;c;{pending_response}\x1b\\")
        wait_for(fd, screen, "READ: pending response")

        # An idle suspension succeeds and resume installs a fresh read lifetime.
        send(fd, "s")
        wait_for(fd, screen, "RESUMED")
        send(fd, "r")
        wait_for_bytes(fd, screen, osc52(b"?"))
        resumed_response = base64.b64encode("after resume".encode()).decode()
        send(fd, f"\x1b]52;c;{resumed_response}\x1b\\")
        wait_for(fd, screen, "READ: after resume")

        # An ignored terminal query remains pending until App destruction.
        send(fd, "r")
        wait_for_bytes(fd, screen, osc52(b"?"))
        send(fd, "\x03")
        status = wait_exit(pid, fd, screen, timeout=2.0)
        if status is None:
            raise AssertionError("clipboard fixture did not cancel its pending read")
        assert status == 0, f"exit status {status}"

        run_event_thread_cancellation()
        print("✓ Cooper OSC 52 clipboard PTY test passed")
    finally:
        cleanup(fd, pid)


def run_event_thread_cancellation():
    pid, fd = spawn(BIN, rows=6, cols=80)
    screen = Screen(6, 80)
    try:
        wait_for(fd, screen, "Clipboard fixture ready")
        send(fd, "b")
        wait_for_bytes(fd, screen, osc52(b"?"))
        status = wait_exit(pid, fd, screen, timeout=2.0)
        if status is None:
            raise AssertionError("background destroy did not cancel an event-thread clipboard read")
        assert status == 0, f"blocked-read exit status {status}"
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
