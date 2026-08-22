#!/usr/bin/env python3
"""Smoke test for Cooper's retained Input vertical slice."""

import os
import signal
import sys

from test_harness import Screen, build, read_for, resize, send, spawn, wait_exit, wait_for

ROOT = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(ROOT, "input")


def main():
    build("input")
    pid, fd = spawn(BIN, rows=8, cols=50)
    screen = Screen(8, 50)
    try:
        wait_for(fd, screen, "Type here")

        send(fd, "hello")
        wait_for(fd, screen, "hello")

        send(fd, "\x1b[D")
        send(fd, "!")
        wait_for(fd, screen, "hell!o")

        send(fd, "\x7f")
        wait_for(fd, screen, "hello")

        resize(fd, rows=8, cols=20)
        send(fd, "x")
        wait_for(fd, screen, "hellxo")
        send(fd, "\x7f")
        wait_for(fd, screen, "hello")

        # Readline-style bindings are normalized by Vaxis and handled by the
        # Ard-native editor action layer.
        send(fd, "\x05")  # Ctrl+E: end
        send(fd, " world")
        wait_for(fd, screen, "hello world")
        send(fd, "\x17")  # Ctrl+W: delete previous word
        for _ in range(8):
            read_for(fd, screen, 0.05)
        assert "world" not in screen.text(), "Ctrl+W did not delete the previous word"

        send(fd, "world")
        wait_for(fd, screen, "hello world")
        send(fd, "\x1bb")  # Alt+B: previous word
        send(fd, "X")
        wait_for(fd, screen, "hello Xworld")
        send(fd, "\x01")  # Ctrl+A: start
        send(fd, ">")
        wait_for(fd, screen, ">hello Xworld")
        send(fd, "\x1b[97;9u")  # Kitty Super+A: select all
        send(fd, "Q")
        wait_for(fd, screen, "Q")

        send(fd, "\x03")
        status = wait_exit(pid, fd, screen, timeout=2.0)
        if status is None:
            raise AssertionError("Cooper input did not exit after Ctrl+C")
        assert status == 0, f"exit status {status}"

        print("✓ Cooper input smoke test passed")
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
