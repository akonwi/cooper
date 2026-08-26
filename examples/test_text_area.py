#!/usr/bin/env python3
"""PTY validation for Cooper's retained multiline TextArea."""

import os
import signal
import sys

from test_harness import Screen, binary_path, build, drain, send, spawn, wait_exit, wait_for

ROOT = os.path.dirname(os.path.abspath(__file__))
BIN = binary_path("text_area")


def main():
    os.chdir(ROOT)
    build("text_area", source="fixtures/text_area.ard")
    pid, fd = spawn(BIN, rows=12, cols=50)
    screen = Screen(12, 50)
    try:
        wait_for(fd, screen, "status: ready")
        wait_for(fd, screen, "Write multiple lines…")

        send(fd, "\t")
        wait_for(fd, screen, "status: focused")
        send(fd, "hello\rworld")
        wait_for(fd, screen, "value: hello↵world")
        drain(fd, screen, 0.1)
        assert "hello" in screen.text() and "world" in screen.text(), "hard lines were not painted"

        # Visual movement and hard-line Home edit the first row while retaining
        # the source newline between both rows.
        send(fd, "\x1b[A")
        send(fd, "\x1b[H")
        send(fd, ">")
        wait_for(fd, screen, "value: >hello↵world")

        # Kitty Super+A exercises complete editable selection replacement.
        send(fd, "\x1b[97;9u")
        send(fd, "replacement")
        wait_for(fd, screen, "value: replacement")

        # Bracketed paste is one multiline input transaction and normalizes
        # CRLF before painting and reporting the retained value.
        send(fd, "\x1b[200~one\r\ntwo\rthree\x1b[201~")
        wait_for(fd, screen, "value: replacementone↵two↵three")

        # Ctrl+Enter is observed before TextArea's default editor and therefore
        # does not insert another newline.
        send(fd, "\x1b[13;5u")
        wait_for(fd, screen, "submit: replacementone↵two↵three")
        send(fd, "!")
        wait_for(fd, screen, "value: replacementone↵two↵three!")

        send(fd, "\r4\r5\r6")
        wait_for(fd, screen, "value: replacementone↵two↵three!↵4↵5↵6")
        assert "┃" in screen.text(), "overflowing TextArea did not show its scrollbar"

        send(fd, "\x03")
        status = wait_exit(pid, fd, screen, timeout=2.0)
        if status is None:
            raise AssertionError("TextArea fixture did not exit after Ctrl+C")
        assert status == 0, f"exit status {status}"
        print("✓ Cooper TextArea PTY test passed")
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
