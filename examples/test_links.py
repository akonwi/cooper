#!/usr/bin/env python3
"""PTY validation for Cooper's OpenTUI-style interactive link demo."""

import os
import signal
import sys

from test_harness import Screen, binary_path, build, drain, resize, send, spawn, wait_exit, wait_for

ROOT = os.path.dirname(os.path.abspath(__file__))
BIN = binary_path("links")


def sgr(fd, code, col, row, final="M"):
    send(fd, f"\x1b[<{code};{col + 1};{row + 1}{final}")


def click(fd, col, row):
    sgr(fd, 0, col, row)
    sgr(fd, 0, col, row, "m")


def drag(fd, start_col, start_row, end_col, end_row):
    sgr(fd, 0, start_col, start_row)
    sgr(fd, 32, end_col, end_row)
    sgr(fd, 0, end_col, end_row, "m")


def main():
    os.chdir(ROOT)
    build("links")
    pid, fd = spawn(BIN, rows=24, cols=100)
    screen = Screen(24, 100)
    try:
        wait_for(fd, screen, "Cooper Interactive Link Demo")
        wait_for(fd, screen, "drag mode: OFF")
        drain(fd, screen, 0.15)

        initial = screen.text()
        for expected in (
            "Click the links to open them.",
            "OSC 8 metadata emitted",
            "♥ Project Info",
            "GitHub Repository",
            "Ard Website",
            "MIT",
            "📚 Documentation",
            "Quick Start",
            "Examples",
            "Application API",
            "👋 Connect",
            "Cooper Issues",
            "Author on GitHub",
        ):
            assert expected in initial, f"missing link-demo specimen {expected!r}"

        # Match the reference demo's roomy 100x24 absolute card geometry.
        assert screen.line(6)[5] == "╭", "project card did not start at 5,6"
        assert screen.line(8)[50] == "╭", "documentation card did not start at 50,8"
        assert screen.line(16)[20] == "╭", "connect card did not start at 20,16"

        # Cards remain fixed while drag mode is disabled.
        drag(fd, start_col=10, start_row=6, end_col=40, end_row=4)
        drain(fd, screen, 0.15)
        assert screen.line(6)[5] == "╭" and "♥ Project Info" in screen.line(7)

        # In drag mode, a stationary plain click on link text is observed but
        # suppressed so grabbing a card cannot unexpectedly launch a browser.
        send(fd, "d")
        wait_for(fd, screen, "drag mode: ON")
        click(fd, col=18, row=9)
        wait_for(fd, screen, "Drag mode blocked: https://github.com/akonwi/cooper")

        # A drag beginning on a different link cancels link activation, raises
        # the project card, and preserves the pointer-to-card offset.
        drag(fd, start_col=17, start_row=10, end_col=47, end_row=8)
        drain(fd, screen, 0.2)
        assert screen.line(4)[35] == "╭", "project card did not preserve its drag offset"
        assert "♥ Project Info" in screen.line(5)
        assert screen.line(6)[5] != "╭", "project card left stale paint at its old position"
        assert screen.line(8)[50] != "╭", "raised project card did not paint over documentation"
        assert "https://ard.run" not in screen.text(), "link drag incorrectly activated Ard Website"

        # Turning drag mode back off freezes the card at its retained position.
        send(fd, "d")
        wait_for(fd, screen, "drag mode: OFF")
        drag(fd, start_col=40, start_row=4, end_col=10, end_row=18)
        drain(fd, screen, 0.15)
        assert screen.line(4)[35] == "╭" and "♥ Project Info" in screen.line(5)

        # A narrow resize clips the source-compatible absolute scene. The next
        # enabled drag clamps the full card back inside the new terminal bounds.
        resize(fd, rows=20, cols=70)
        narrow = Screen(20, 70)
        wait_for(fd, narrow, "Cooper Interactive Link Demo")
        wait_for(fd, narrow, "drag mode: OFF")
        drain(fd, narrow, 0.15)
        assert "👋 Connect" in narrow.text(), "narrow scene lost an unobscured retained card"

        send(fd, "d")
        wait_for(fd, narrow, "drag mode: ON")
        drag(fd, start_col=40, start_row=4, end_col=69, end_row=19)
        drain(fd, narrow, 0.2)
        assert narrow.line(12)[30] == "╭", "horizontal/vertical drag clamping failed"
        assert narrow.line(19)[30] == "╰", "clamped project card exceeded terminal height"

        # OpenTUI floors its clamp after applying the viewport ceiling. Keep
        # that behavior when the viewport itself is smaller than the card.
        drag(fd, start_col=35, start_row=12, end_col=5, end_row=0)
        drain(fd, narrow, 0.15)
        resize(fd, rows=7, cols=30)
        tiny = Screen(7, 30)
        wait_for(fd, tiny, "♥ Project Info")
        drag(fd, start_col=5, start_row=0, end_col=20, end_row=5)
        drain(fd, tiny, 0.15)
        assert tiny.line(0)[0] == "╭", "undersized viewport produced a negative card position"

        send(fd, "\x03")
        status = wait_exit(pid, fd, tiny, timeout=2.0)
        if status is None:
            raise AssertionError("interactive link demo did not exit after Ctrl+C")
        assert status == 0, f"exit status {status}"

        print("✓ Cooper OpenTUI-style interactive link PTY test passed")
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
