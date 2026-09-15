#!/usr/bin/env python3
"""Exercise real Cooper output against a Kitty-capable PTY protocol peer."""

import base64
import fcntl
import os
import pty
import re
import signal
import struct
import termios

from test_harness import binary_path, build, drain, send, wait_exit, wait_for
from test_image import CaptureScreen


class KittyScreen(CaptureScreen):
    def __init__(self, fd, rows, cols):
        super().__init__(rows, cols)
        self.fd = fd
        self.query = b""

    def feed(self, data):
        self.query = (self.query + data)[-65536:]
        if b"\x1b_Gi=1,a=q\x1b\\" in self.query:
            os.write(self.fd, b"\x1b_Gi=1;OK\x1b\\")
            self.query = b""
        super().feed(data)


def commands(data):
    result = []
    for packet in re.findall(rb"\x1b_G(.*?)\x1b\\", data, re.S):
        header, _, payload = packet.partition(b";")
        fields = dict(part.split(b"=", 1) for part in header.split(b",") if b"=" in part)
        result.append((fields, payload))
    return result


def placements(data):
    return [dict((k.decode(), int(v)) for k, v in fields.items() if k != b"a")
            for fields, _ in commands(data) if fields.get(b"a") == b"p"]


def uploads(data):
    return [fields for fields, _ in commands(data) if fields.get(b"a") == b"t"]


def size(fd, rows, cols):
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, cols * 10, rows * 20))


def main():
    build("image")
    ready_read, ready_write = os.pipe()
    pid, fd = pty.fork()
    if pid == 0:
        os.close(ready_write)
        os.read(ready_read, 1)
        os.close(ready_read)
        os.environ.update(TERM="xterm-256color", COLORTERM="truecolor", VAXIS_LOG_LEVEL="error")
        os.environ.pop("VAXIS_GRAPHICS", None)  # Capability query, not a forced mode.
        binary = binary_path("image")
        os.execv(binary, [binary])
    os.close(ready_read)
    size(fd, 28, 90)
    os.write(ready_write, b"1")
    os.close(ready_write)
    screen = KittyScreen(fd, 28, 90)
    try:
        wait_for(fd, screen, "READY")
        drain(fd, screen, 0.15)
        # Startup can include a Vaxis full refresh after its first frame.
        assert uploads(screen.output), "expected detected Kitty upload"
        assert len({u[b"i"] for u in uploads(screen.output)}) == 1
        initial = placements(screen.output)
        assert initial and all(p == initial[0] for p in initial)
        assert initial[0]["y"] == 0
        assert initial[0]["r"] == 21 and initial[0]["c"] == 84
        assert "▀" not in screen.text(), "native path also painted cell fallback"
        encoded = b""
        for fields, payload in commands(screen.output):
            if payload and fields.get(b"a") != b"q":
                encoded += payload
                if fields.get(b"m") == b"0":
                    break
        png = base64.b64decode(encoded)
        assert png[:8] == b"\x89PNG\r\n\x1a\n"
        assert struct.unpack(">II", png[16:24]) == (96, 64), "source was downsampled before upload"

        start = len(screen.output)
        send(fd, "\x1b[B")
        wait_for(fd, screen, "Scroll: 1")
        drain(fd, screen, 0.1)
        scrolled = screen.output[start:]
        assert not uploads(scrolled), "scroll retransmitted source pixels"
        assert placements(scrolled)[0]["y"] == 2, "scroll did not crop source coordinates"

        start = len(screen.output)
        send(fd, "p")
        wait_for(fd, screen, "A popup above the image.")
        drain(fd, screen, 0.1)
        popup = screen.output[start:]
        assert len(placements(popup)) == 4, "expected four native regions around popup"
        assert not uploads(popup), "popup retransmitted source pixels"
        start = len(screen.output)
        send(fd, "p")
        drain(fd, screen, 0.2)
        assert len(placements(screen.output[start:])) == 1, "popup removal did not restore full placement"

        start = len(screen.output)
        send(fd, "s")
        wait_for(fd, screen, "RESUMED")
        drain(fd, screen, 0.1)
        assert uploads(screen.output[start:]), "resume did not reupload terminal resources"

        size(fd, 22, 60)
        narrow = KittyScreen(fd, 22, 60)
        wait_for(fd, narrow, "RESUMED")
        drain(fd, narrow, 0.1)
        assert placements(narrow.output), "resize did not recreate native placement"
        assert "▀" not in narrow.text()
        send(fd, "q")
        assert wait_exit(pid, fd, narrow) == 0
        drain(fd, narrow, 0.1)
        assert any(fields.get(b"d") == b"I" for fields, _ in commands(narrow.output)), "quit did not delete image data"
        print("✓ Native Kitty PTY test passed (detection, full-resolution upload, cached crops, popup, resize, resume, cleanup)")
    finally:
        os.close(fd)
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass


if __name__ == "__main__":
    main()
