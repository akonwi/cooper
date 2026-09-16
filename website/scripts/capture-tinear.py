#!/usr/bin/env python3
# /// script
# dependencies = ["pyte==0.8.2", "pillow==12.1.1"]
# ///
"""Render a real 126×28 Tinear PTY frame. Run with `uv run scripts/capture-tinear.py`."""

import os
from pathlib import Path
import re
import signal
import sys

import pyte
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "examples"))
from test_harness import Screen, build, drain, send, spawn, wait_exit, wait_for


class Capture(Screen):
    def __init__(self):
        super().__init__(28, 126)
        self.output = bytearray()

    def feed(self, data):
        self.output.extend(data)
        super().feed(data)


def main():
    binary = build("cui_tinear")
    pid, fd = spawn(binary, rows=28, cols=126)
    capture = Capture()
    try:
        wait_for(fd, capture, "Polish command palette search")
        drain(fd, capture, 0.3)
        terminal = pyte.Screen(126, 28)
        # Vaxis emits colon-separated SGR; pyte accepts the equivalent semicolons.
        ansi = re.sub(rb"\x1b\[([0-9:;]*)m", lambda m: b"\x1b[" + m[1].replace(b":", b";") + b"m", capture.output)
        pyte.ByteStream(terminal).feed(ansi)
        assert "Polish command palette search" in "\n".join(terminal.display)
        image = Image.new("RGB", (2520, 1008), "#11171e")
        draw = ImageDraw.Draw(image)
        font_dir = Path("/usr/share/fonts/truetype/dejavu")
        normal = ImageFont.truetype(str(font_dir / "DejaVuSansMono.ttf"), 30)
        bold = ImageFont.truetype(str(font_dir / "DejaVuSansMono-Bold.ttf"), 30)
        palette = {"black": "10151c", "red": "e06c75", "green": "98c379", "brown": "e5c07b", "blue": "61afef", "magenta": "c678dd", "cyan": "56b6c2", "white": "dce2ea"}
        palette.update({"bright" + name: value for name, value in palette.copy().items()})
        palette.update(brightblack="677485", brightwhite="ffffff")

        def color(value, default):
            return "#" + (default if value == "default" else palette.get(value, value))

        for row in range(28):
            for col in range(126):
                cell = terminal.buffer[row][col]
                fg, bg = color(cell.fg, "dce2ea"), color(cell.bg, "11171e")
                if cell.reverse:
                    fg, bg = bg, fg
                x, y = col * 20, row * 36
                draw.rectangle((x, y, x + 19, y + 35), fill=bg)
                draw.text((x, y - 1), cell.data, font=bold if cell.bold else normal, fill=fg)
        destination = ROOT / "website/public/tinear.png"
        image.save(destination, optimize=True)
        print(f"Captured actual Tinear output: {destination}")
    finally:
        send(fd, "\x03")
        if wait_exit(pid, fd, capture) is None:
            os.kill(pid, signal.SIGTERM)
            os.waitpid(pid, 0)
        os.close(fd)


if __name__ == "__main__":
    main()
