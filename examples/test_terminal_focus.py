#!/usr/bin/env python3
"""PTY validation for Cooper's OpenTUI-style focus restore demo."""

import os
import signal
import sys

from test_harness import Screen, binary_path, build, drain, resize, send, spawn, wait_exit, wait_for

ROOT = os.path.dirname(os.path.abspath(__file__))
BIN = binary_path("terminal_focus")


def sgr(fd, code, col, row):
    send(fd, f"\x1b[<{code};{col + 1};{row + 1}M")


def move(fd, col, row):
    sgr(fd, 35, col, row)


def wheel_up(fd, col, row):
    sgr(fd, 64, col, row)


def main():
    os.chdir(ROOT)
    build("terminal_focus")
    pid, fd = spawn(BIN, rows=24, cols=100)
    screen = Screen(24, 100)
    try:
        wait_for(fd, screen, "Focus Restore Demo - Mouse Tracking + Terminal Mode Restore")
        wait_for(fd, screen, "Focus: UNKNOWN  (waiting for terminal report)")
        wait_for(fd, screen, "Event Log (latest 20)")
        drain(fd, screen, 0.15)

        initial = screen.text()
        for expected in (
            "Alt-tab away and back",
            "Mouse: (0, 0) | Move events: 0",
            "Focus-in: 0 | Focus-out: 0 | Mouse resumes: 0",
            "Demo started. Move mouse",
        ):
            assert expected in initial, f"missing focus-restore specimen {expected!r}"

        # The full-screen listener reports pointer activity regardless of which
        # retained status/log child is physically under the pointer.
        move(fd, col=15, row=5)
        wait_for(fd, screen, "Mouse: (15, 5) | Move events: 1")
        move(fd, col=16, row=5)
        move(fd, col=17, row=5)
        wait_for(fd, screen, "Focus: UNKNOWN  (no reports; terminal may not support them)")
        wait_for(fd, screen, "Mouse: (17, 5) | Move events: 3")

        # Terminal focus is deduplicated independently from pointer state.
        send(fd, "\x1b[O")
        wait_for(fd, screen, "Focus: NO   (modes may be stripped by terminal)")
        wait_for(fd, screen, "Focus-in: 0 | Focus-out: 1 | Mouse resumes: 0")
        send(fd, "\x1b[O")
        drain(fd, screen, 0.1)
        assert "Focus-in: 0 | Focus-out: 1 | Mouse resumes: 0" in screen.text()

        send(fd, "\x1b[I")
        wait_for(fd, screen, "Focus: YES  (awaiting physical mouse input)")
        wait_for(fd, screen, "Focus-in: 1 | Focus-out: 1 | Mouse resumes: 0")
        send(fd, "\x1b[I")
        drain(fd, screen, 0.1)
        assert "Focus-in: 1 | Focus-out: 1 | Mouse resumes: 0" in screen.text()

        # The first pointer event after focus-in is the observable restoration
        # check; later events do not inflate the resume counter.
        move(fd, col=18, row=7)
        wait_for(fd, screen, "Focus-in: 1 | Focus-out: 1 | Mouse resumes: 1")
        wait_for(fd, screen, "Focus: YES  (mouse tracking active)")
        wait_for(fd, screen, "MOUSE RESUMED - tracking active after focus #1")
        move(fd, col=19, row=7)
        drain(fd, screen, 0.1)
        assert "Mouse resumes: 1" in screen.text()

        # Fill beyond the bounded 20-entry history. The followed viewport keeps
        # the latest focus-out/focus-in/resume triplet visible.
        for cycle in range(2, 9):
            send(fd, "\x1b[O")
            wait_for(fd, screen, f"Focus-out: {cycle}")
            send(fd, "\x1b[I")
            wait_for(fd, screen, f"Focus-in: {cycle}")
            move(fd, col=20 + cycle, row=7 + cycle % 3)
            wait_for(fd, screen, f"Mouse resumes: {cycle}")

        drain(fd, screen, 0.2)
        final = screen.text()
        assert "Focus-in: 8 | Focus-out: 8 | Mouse resumes: 8" in final
        assert "MOUSE RESUMED - tracking active after focus #8" in final
        assert "Demo started. Move mouse" not in final, "bounded log retained its evicted first row"

        # Inspecting the top of history proves the cap, not merely follow mode:
        # after 25 total entries, the oldest retained row is focus-in #2.
        for _ in range(8):
            wheel_up(fd, col=5, row=20)
        wait_for(fd, screen, "FOCUS IN #2 - waiting for physical mouse input")
        assert "FOCUS OUT #1" not in screen.text()

        resize(fd, rows=20, cols=70)
        narrow = Screen(20, 70)
        wait_for(fd, narrow, "Focus Restore Demo")
        wait_for(fd, narrow, "Focus-in: 8 | Focus-out: 8 | Mouse resumes: 8")
        wait_for(fd, narrow, "Event Log (latest 20)")
        drain(fd, narrow, 0.15)
        bottoms = [line for line in narrow.text().splitlines() if line.startswith(" ╰")]
        assert len(bottoms) >= 2 and all(line.endswith("╯") for line in bottoms), "compact focus panels lost their borders"

        send(fd, "\x03")
        status = wait_exit(pid, fd, narrow, timeout=2.0)
        if status is None:
            raise AssertionError("focus restore demo did not exit after Ctrl+C")
        assert status == 0, f"exit status {status}"

        print("✓ Cooper OpenTUI-style focus restore PTY test passed")
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
