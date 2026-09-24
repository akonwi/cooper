#!/usr/bin/env python3
"""PTY coverage for the scoped CUI keymap example."""

import html
import os
import signal
from pathlib import Path

from test_harness import Screen, build, drain, send, spawn, wait_exit, wait_for


def capture(screen, name):
    """Export the PTY emulator's actual text cells (without terminal colors)."""
    directory = os.environ.get("COOPER_KEYMAP_CAPTURE_DIR")
    if directory:
        rows = screen.text().splitlines()
        svg = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="{len(rows) * 26 + 32}">',
            '<rect width="100%" height="100%" fill="#17202c"/>',
        ]
        for index, line in enumerate(rows):
            svg.append(
                f'<text x="16" y="{36 + index * 26}" fill="#edf3fa" '
                f'font-family="DejaVu Sans Mono" font-size="18" xml:space="preserve">'
                f'{html.escape(line)}</text>'
            )
        svg.append("</svg>")
        (Path(directory) / f"{name}.svg").write_text("".join(svg))


def run_editor(binary):
    pid, fd = spawn(binary, rows=16, cols=80)
    screen = Screen(16, 80)
    try:
        wait_for(fd, screen, "Scoped keymap editor")

        # Input's normal editing and Return submit behavior remain available.
        send(fd, "draft")
        wait_for(fd, screen, "text=draft")
        send(fd, "\r")
        wait_for(fd, screen, "submits=1")
        capture(screen, "keymaps-dirty")

        # Ctrl+S receives current mutable text lazily and becomes disabled once clean.
        send(fd, "\x13")
        wait_for(fd, screen, "saved=draft saves=1")
        wait_for(fd, screen, "Save [editor] · disabled")
        capture(screen, "keymaps-saved")
        send(fd, "\x13")
        drain(fd, screen, 0.15)
        assert "saved=draft saves=1" in screen.text(), "disabled Save executed"

        # A raw handler sees Ctrl+P first and prevents its mapped command.
        send(fd, "\x10")
        wait_for(fd, screen, "blocked=1")
        assert "blocked=101" not in screen.text(), "prevented command executed"

        # Footer content comes from keymap discovery and Key.label(), not literals.
        text = screen.text()
        assert "Ctrl+S  Save [editor]" in text
        assert "Ctrl+C  Mapped Ctrl+C [reserved] · reserved" in text

        send(fd, "\x11")
        status = wait_exit(pid, fd, screen)
        assert status is not None and os.waitstatus_to_exitcode(status) == 0
    finally:
        os.close(fd)
        try:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
        except (ProcessLookupError, ChildProcessError):
            pass


def run_ctrl_c_policy(binary):
    pid, fd = spawn(binary, rows=16, cols=80)
    screen = Screen(16, 80)
    try:
        wait_for(fd, screen, "Mapped Ctrl+C")
        send(fd, "\x03")
        status = wait_exit(pid, fd, screen)
        assert status is not None and os.waitstatus_to_exitcode(status) == 0
    finally:
        os.close(fd)
        try:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
        except (ProcessLookupError, ChildProcessError):
            pass


def main():
    os.chdir(Path(__file__).parent)
    binary = build("keymaps")
    run_editor(binary)
    run_ctrl_c_policy(binary)
    print("keymaps PTY test passed")


if __name__ == "__main__":
    main()
