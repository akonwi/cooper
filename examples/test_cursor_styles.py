#!/usr/bin/env python3
"""PTY validation for Cooper's cursor style example."""

import os
import signal
import sys

from test_harness import Screen, binary_path, build, drain, send, spawn, wait_exit, wait_for

ROOT = os.path.dirname(os.path.abspath(__file__))
BIN = binary_path("cursor_styles")

USER_STYLE_QUERY = b"\x1bP$q q\x1b\\"
# Pretend the user's terminal currently shows a steady block (DECSCUSR 2).
USER_STYLE_REPLY = b"\x1bP1$r2 q\x1b\\"


def decscusr(value):
    return f"\x1b[{value} q".encode()


class RecordingScreen(Screen):
    """Screen that also keeps raw output and answers the cursor style query."""

    def __init__(self, fd, rows, cols):
        super().__init__(rows, cols)
        self.fd = fd
        self.raw = b""
        self.answered = False

    def feed(self, data):
        self.raw += data
        if not self.answered and USER_STYLE_QUERY in self.raw:
            self.answered = True
            os.write(self.fd, USER_STYLE_REPLY)
        super().feed(data)

    def mark(self):
        return len(self.raw)

    def since(self, mark):
        return self.raw[mark:]


def expect_style(fd, screen, mark, value, needle):
    wait_for(fd, screen, needle)
    drain(fd, screen, 0.2)
    output = screen.since(mark)
    if decscusr(value) not in output:
        raise AssertionError(f"expected DECSCUSR {value} after {needle!r}, got {output!r}")
    last = output.rfind(b" q")
    start = output.rfind(b"\x1b[", 0, last)
    if output[start:last + 2] != decscusr(value):
        raise AssertionError(
            f"expected final DECSCUSR {value} after {needle!r}, got {output[start:last + 2]!r}"
        )


def main():
    os.chdir(ROOT)
    build("cursor_styles")
    pid, fd = spawn(BIN, rows=24, cols=100)
    screen = RecordingScreen(fd, 24, 100)
    try:
        wait_for(fd, screen, "FOCUS input")
        wait_for(fd, screen, "INPUT terminal  TEXT_AREA terminal")
        drain(fd, screen, 0.3)
        if not screen.answered:
            raise AssertionError("expected Vaxis to query the user's cursor style")
        if decscusr(0) not in screen.raw:
            raise AssertionError("expected terminal-default DECSCUSR 0 at startup")

        mark = screen.mark()
        send(fd, "\x14")  # Ctrl+T
        expect_style(fd, screen, mark, 2, "INPUT block")

        mark = screen.mark()
        send(fd, "\x14")
        expect_style(fd, screen, mark, 1, "INPUT blinking_block")

        mark = screen.mark()
        send(fd, "\t")
        expect_style(fd, screen, mark, 0, "FOCUS text_area")

        mark = screen.mark()
        send(fd, "\x0f")  # Ctrl+O
        expect_style(fd, screen, mark, 6, "MODE INSERT")
        wait_for(fd, screen, "INPUT beam  TEXT_AREA beam")

        mark = screen.mark()
        send(fd, "\x1b")
        expect_style(fd, screen, mark, 2, "MODE NORMAL")

        send(fd, "zz")
        drain(fd, screen, 0.3)
        if "zz" in screen.text():
            raise AssertionError("expected NORMAL mode to swallow text input")

        mark = screen.mark()
        send(fd, "i")
        expect_style(fd, screen, mark, 6, "MODE INSERT")

        mark = screen.mark()
        send(fd, "\x0f")
        expect_style(fd, screen, mark, 0, "MODE off")

        mark = screen.mark()
        send(fd, "\x03")
        status = wait_exit(pid, fd, screen, timeout=3.0)
        if status is None:
            raise AssertionError("cursor styles demo did not exit after Ctrl+C")
        assert status == 0, f"exit status {status}"
        drain(fd, screen, 0.1)
        exit_output = screen.since(mark)
        if decscusr(2) not in exit_output:
            raise AssertionError(f"expected user cursor style restore on exit, got {exit_output!r}")

        print("✓ Cooper cursor styles PTY test passed")
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
