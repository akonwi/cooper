#!/usr/bin/env python3
"""Image prototype: PTY clipping, overlays, resize, suspend/resume and cleanup."""

import os
from pathlib import Path
import signal

from test_harness import Screen, binary_path, build, drain, resize, send, spawn, wait_exit, wait_for


class CaptureScreen(Screen):
    def __init__(self, rows, cols):
        super().__init__(rows, cols)
        self.output = bytearray()

    def feed(self, data):
        self.output.extend(data)
        super().feed(data)

    def capture(self, name):
        # Optional real terminal output for visual review in a terminal emulator.
        destination = os.environ.get("COOPER_IMAGE_CAPTURES")
        if destination:
            Path(destination).mkdir(parents=True, exist_ok=True)
            Path(destination, name + ".ansi").write_bytes(self.output)


def main():
    build("image")
    pid, fd = spawn(binary_path("image"), rows=28, cols=90)
    screen = CaptureScreen(28, 90)
    try:
        wait_for(fd, screen, "Scroll: 0")
        drain(fd, screen, 0.1)
        assert screen.line(3).startswith("╭") and screen.line(25).endswith("╯")
        assert "▀" in screen.line(4), "image did not paint"
        assert "▀" not in screen.line(26), "image escaped the viewport into status"
        screen.capture("image-initial")

        # The retained image is taller than its viewport. Scroll partially out.
        for _ in range(7):
            send(fd, "\x1b[B")
        wait_for(fd, screen, "Scroll: 7")
        drain(fd, screen, 0.1)
        assert screen.line(3).startswith("╭") and screen.line(25).endswith("╯")
        assert "▀" in screen.line(4) and "▀" not in screen.line(26)
        before_popup = screen.text()
        screen.capture("image-scrolled")
        send(fd, "p")
        wait_for(fd, screen, "A popup above the image.")
        drain(fd, screen, 0.1)
        assert "Press P to reveal the pixels again." in screen.text()
        screen.capture("image-popup")
        send(fd, "p")
        drain(fd, screen, 0.2)
        assert screen.text() == before_popup, "hiding popup did not restore the exact cell frame"

        send(fd, "s")
        wait_for(fd, screen, "RESUMED")
        drain(fd, screen, 0.1)
        assert screen.line(4) == before_popup.splitlines()[4]
        assert b"\x1b[?1049l" in screen.output, "suspend did not leave alternate screen"
        assert screen.output.count(b"\x1b[?1049h") >= 2, "resume did not reacquire terminal"
        screen.capture("image-resumed")

        resize(fd, rows=22, cols=60)
        narrow = CaptureScreen(22, 60)
        wait_for(fd, narrow, "RESUMED")
        drain(fd, narrow, 0.1)
        assert narrow.line(3).startswith("╭") and narrow.line(19).endswith("╯")
        assert "▀" in narrow.line(4) and "▀" not in narrow.line(20)
        narrow.capture("image-narrow")
        send(fd, "q")
        assert wait_exit(pid, fd, narrow) == 0, "image example did not exit cleanly"
        # wait_exit can reap the child before reading its final PTY bytes.
        drain(fd, narrow, 0.1)
        assert b"\x1b[?1049l" in narrow.output, "quit did not restore terminal"
        print("✓ Cooper image PTY test passed (scroll, popup, resize, suspend/resume, quit)")
    finally:
        os.close(fd)
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass


if __name__ == "__main__":
    main()
