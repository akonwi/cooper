#!/usr/bin/env python3
"""PTY validation for Cooper terminal-mediated desktop notifications."""

import os
import signal
import sys
import time

from test_harness import Screen, binary_path, build, read_for, send, spawn, wait_exit, wait_for

ROOT = os.path.dirname(os.path.abspath(__file__))
BIN = binary_path("notification")


def wait_for_bytes(fd, screen, needle, timeout=4.0):
    captured = b""
    deadline = time.time() + timeout
    while time.time() < deadline:
        captured += read_for(fd, screen, 0.05)
        if needle in captured:
            return captured
    raise AssertionError(f"did not see terminal bytes {needle!r}; captured {captured!r}")


def wait_for_text_and_bytes(fd, screen, text, needles, timeout=4.0):
    captured = b""
    deadline = time.time() + timeout
    while time.time() < deadline:
        captured += read_for(fd, screen, 0.05)
        if text in screen.text() and all(needle in captured for needle in needles):
            return captured
    raise AssertionError(
        f"did not see {text!r} and {needles!r}; captured {captured!r}; screen:\n{screen.text()}"
    )


def wait_exit_with_bytes(pid, fd, screen, timeout=2.0):
    captured = b""
    deadline = time.time() + timeout
    while time.time() < deadline:
        captured += read_for(fd, screen, 0.05)
        done, status = os.waitpid(pid, os.WNOHANG)
        if done == pid:
            return status, captured
    return None, captured


def run_supported():
    pid, fd = spawn(
        BIN,
        rows=5,
        cols=80,
        env={
            "COOPER_NOTIFICATION_PROTOCOL": "osc777",
            "COOPER_TERMINAL_PROGRESS": "1",
        },
    )
    screen = Screen(5, 80)
    try:
        wait_for(fd, screen, "Notification fixture ready")

        send(fd, "t")
        wait_for_bytes(fd, screen, b"\x1b]2;Cooper Title\x1b\\")
        wait_for(fd, screen, "TITLE ACCEPTED: true")

        send(fd, "n")
        wait_for_bytes(fd, screen, b"\x1b]777;notify;Cooper;Build finished\x1b\\")
        wait_for(fd, screen, "TITLED ACCEPTED")

        send(fd, "u")
        wait_for_bytes(fd, screen, b"\x1b]777;notify;Untitled notification;\x1b\\")
        wait_for(fd, screen, "UNTITLED ACCEPTED")

        send(fd, "i")
        wait_for_bytes(fd, screen, b"\x1b]9;4;3\x1b\\")
        wait_for(fd, screen, "PROGRESS INDETERMINATE: true")

        send(fd, "d")
        wait_for_bytes(fd, screen, b"\x1b]9;4;1;42\x1b\\")
        wait_for(fd, screen, "PROGRESS NORMAL: true")

        send(fd, "e")
        wait_for_bytes(fd, screen, b"\x1b]9;4;2;75\x1b\\")
        wait_for(fd, screen, "PROGRESS ERROR: true")

        send(fd, "p")
        wait_for_bytes(fd, screen, b"\x1b]9;4;4;25\x1b\\")
        wait_for(fd, screen, "PROGRESS PAUSED: true")

        send(fd, "r")
        wait_for_bytes(fd, screen, b"\x1b]9;4;0\x1b\\")
        wait_for(fd, screen, "PROGRESS REMOVED: true")

        send(fd, "i")
        wait_for_bytes(fd, screen, b"\x1b]9;4;3\x1b\\")
        send(fd, "s")
        suspend_output = wait_for_text_and_bytes(
            fd,
            screen,
            "SUSPENDED REJECTED · RESUMED",
            [
                b"\x1b]9;4;0\x1b\\",
                b"\x1b]2;Cooper Suspended\x1b\\",
                b"\x1b]9;4;3\x1b\\",
            ],
        )
        if suspend_output.count(b"\x1b]2;Cooper Suspended\x1b\\") != 1:
            raise AssertionError("suspended title was duplicated during resume")
        send(fd, "r")
        wait_for_bytes(fd, screen, b"\x1b]9;4;0\x1b\\")

        send(fd, "i")
        wait_for_bytes(fd, screen, b"\x1b]9;4;3\x1b\\")
        send(fd, "\x03")
        status, shutdown_output = wait_exit_with_bytes(pid, fd, screen)
        assert status == 0, f"exit status {status}"
        if b"\x1b]9;4;0\x1b\\" not in shutdown_output:
            raise AssertionError("active terminal progress was not removed during teardown")
        if b"\x1b]2;" in shutdown_output:
            raise AssertionError("terminal title was unexpectedly changed during teardown")
    finally:
        cleanup(fd, pid)


def run_disabled():
    pid, fd = spawn(
        BIN,
        rows=5,
        cols=80,
        env={
            "COOPER_NOTIFICATION_PROTOCOL": "osc777",
            "COOPER_NOTIFICATIONS": "0",
            "COOPER_TERMINAL_PROGRESS": "0",
        },
    )
    screen = Screen(5, 80)
    try:
        wait_for(fd, screen, "Notification fixture ready")
        send(fd, "n")
        captured = wait_for_text_and_bytes(fd, screen, "TITLED REJECTED", [])
        if b"]777;notify" in captured:
            raise AssertionError("disabled notification emitted OSC 777")
        send(fd, "i")
        progress_output = wait_for_text_and_bytes(
            fd,
            screen,
            "PROGRESS INDETERMINATE: false",
            [],
        )
        if b"]9;4;" in progress_output:
            raise AssertionError("disabled terminal progress emitted OSC 9;4")
        send(fd, "\x03")
        status = wait_exit(pid, fd, screen, timeout=2.0)
        assert status == 0, f"disabled exit status {status}"
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


def main():
    os.chdir(ROOT)
    build("notification", source="fixtures/notification.ard")
    run_supported()
    run_disabled()
    print("✓ Cooper notification PTY test passed")


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"FAIL: {err}", file=sys.stderr)
        sys.exit(1)
