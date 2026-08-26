#!/usr/bin/env python3
"""PTY validation for Cooper's interactive Input laboratory."""

import os
import signal
import sys

from test_harness import Screen, binary_path, build, drain, resize, send, spawn, wait_exit, wait_for

ROOT = os.path.dirname(os.path.abspath(__file__))
BIN = binary_path("input_lab")


def click(fd, col, row):
    send(fd, f"\x1b[<0;{col + 1};{row + 1}M")
    send(fd, f"\x1b[<0;{col + 1};{row + 1}m")


def drag(fd, start_col, row, end_col):
    send(fd, f"\x1b[<0;{start_col + 1};{row + 1}M")
    send(fd, f"\x1b[<32;{end_col + 1};{row + 1}M")
    send(fd, f"\x1b[<0;{end_col + 1};{row + 1}m")


def selected_value(screen):
    lines = screen.text().splitlines()
    row = next(index for index, line in enumerate(lines) if "SELECTION" in line)
    return lines[row + 1]


def main():
    os.chdir(ROOT)
    build("input_lab")
    pid, fd = spawn(BIN, rows=24, cols=80)
    screen = Screen(24, 80)
    try:
        wait_for(fd, screen, "FOCUS  none")
        wait_for(fd, screen, "Ada Lovelace")
        drain(fd, screen, 0.2)

        initial = screen.text()
        for expected in (
            "COOPER INPUT LAB",
            "Ada Lovelace",
            "name@example.com",
            "élan🙂",
            "still editable",
            "input 0 · change 0",
            "submit 0 · reject 0",
            "paste bytes 0",
            "EMAIL  untouched",
        ):
            assert expected in initial, f"missing input-lab specimen {expected!r}"

        # Explicit traversal establishes the first focus only after terminal
        # startup. A one-grapheme submit is rejected on both press and repeat.
        send(fd, "\t")
        wait_for(fd, screen, "FOCUS  NAME")
        send(fd, "A")
        wait_for(fd, screen, "input · NAME · A")
        send(fd, "\r")
        wait_for(fd, screen, "submit 0 · reject 1")
        send(fd, "\x1b[13;1:2u")  # Kitty Return repeat.
        wait_for(fd, screen, "submit 0 · reject 2")
        assert "NAME · REJECTED (<2)" in screen.text()

        # On the now non-empty field, mouse placement inserts at local column
        # zero and a drag selects the complete value for replacement.
        send(fd, "da")
        wait_for(fd, screen, "Ada")
        click(fd, col=2, row=7)
        send(fd, ">")
        wait_for(fd, screen, ">Ada")
        drag(fd, start_col=2, row=7, end_col=6)
        drain(fd, screen, 0.15)
        assert ">Ada" in selected_value(screen), "mouse drag did not select the Input value"
        send(fd, "Ada")
        wait_for(fd, screen, "input 7 · change 0")
        send(fd, "\r")
        wait_for(fd, screen, "submit 1 · reject 2")
        assert "change 1" in screen.text(), "submit did not commit pending change"

        # Explicit Tab traversal focuses Email. Validation is application-owned
        # and updates retained title, border/text style, and diagnostics live.
        send(fd, "\t")
        wait_for(fd, screen, "FOCUS  EMAIL")
        send(fd, "ada@invalid")
        wait_for(fd, screen, "ada@invalid")
        assert "EMAIL · SHAPE INVALID" in screen.text()
        assert "input 18 · change 1" in screen.text(), "email input callbacks were duplicated or dropped"

        # Kitty Super+A exercises Input selection and App selection reporting;
        # typing replaces the selected value and clears the global selection.
        send(fd, "\x1b[97;9u")
        wait_for(fd, screen, "ada@invalid")
        drain(fd, screen, 0.1)
        assert screen.text().count("ada@invalid") == 2, "selected email was not reported globally"
        send(fd, "ada@example.com")
        wait_for(fd, screen, "ada@example.com")
        assert "EMAIL · SHAPE VALID" in screen.text()
        assert "input 33 · change 1" in screen.text(), "selection replacement emitted unexpected input callbacks"

        send(fd, "\x1b[97;9u")
        drain(fd, screen, 0.1)
        assert screen.text().count("ada@example.com") == 2, "valid email selection was not reported"
        send(fd, "\x1b")
        wait_for(fd, screen, "SELECTION")
        drain(fd, screen, 0.1)
        assert screen.text().count("ada@example.com") == 1, "Escape did not clear global selection"

        # Unicode starts with a combining grapheme. A multibyte terminal paste
        # replaces it and proves max_length counts graphemes rather than bytes.
        send(fd, "\t")
        wait_for(fd, screen, "FOCUS  UNICODE")
        assert "change 2" in screen.text(), "Email blur did not emit change"
        send(fd, "\x1b[97;9u")
        drain(fd, screen, 0.1)
        send(fd, "\x1b[200~é🙂你好abcdef\x1b[201~")
        wait_for(fd, screen, "paste bytes 19")
        wait_for(fd, screen, "abcd")
        assert "abcdef" not in screen.text(), "grapheme max_length did not truncate terminal paste"
        assert "input 34 · change 2" in screen.text(), "Unicode paste emitted unexpected input callbacks"

        # Select-all intentionally does nothing for the non-selectable field;
        # editing remains enabled and therefore appends at its existing cursor.
        send(fd, "\t")
        wait_for(fd, screen, "FOCUS  LOCAL EDIT")
        send(fd, "\x1b[97;9u")
        drain(fd, screen, 0.1)
        assert "none" in screen.text(), "non-selectable Input entered global selection"
        send(fd, "X")
        wait_for(fd, screen, "still editableX")
        assert "input 35 · change 3" in screen.text(), "non-selectable edit emitted unexpected callbacks"

        # Readline-style actions remain part of the focused Input contract.
        # Selection is disabled for this field, but word and cursor editing are
        # still available through normalized terminal key chords.
        send(fd, "\x17")  # Ctrl+W: delete previous word.
        drain(fd, screen, 0.1)
        assert "editableX" not in screen.text(), "Ctrl+W did not delete the previous word"
        send(fd, "editableX")
        wait_for(fd, screen, "still editableX")
        send(fd, "\x1bb")  # Alt+B: previous word.
        send(fd, ">")
        wait_for(fd, screen, "still >editableX")
        send(fd, "\x01")  # Ctrl+A: start.
        send(fd, "<")
        wait_for(fd, screen, "<still >editableX")
        send(fd, "\x05")  # Ctrl+E: end.
        send(fd, "!")
        wait_for(fd, screen, "<still >editableX!")
        send(fd, "\x7f")
        wait_for(fd, screen, "<still >editableX")

        # Focus reveal keeps the fourth retained field visible in a compact
        # scrolling viewport without allowing child paint across panel borders.
        resize(fd, rows=18, cols=70)
        compact = Screen(18, 70)
        wait_for(fd, compact, "FOCUS  LOCAL EDIT")
        wait_for(fd, compact, "<still >editableX")
        drain(fd, compact, 0.2)
        assert "LOCAL EDIT · GLOBAL SELECT OFF" in compact.text()
        panel_bottom = next(line for line in compact.text().splitlines() if line.startswith("╰"))
        assert panel_bottom.count("╯") == 2, "compact form content overwrote panel borders"
        assert compact.line(17).endswith("┘"), "compact footer overwrote its border"

        # Editing remains cursor-relative after a narrower layout recomputes
        # the Input viewport.
        send(fd, "\x1b[D")
        send(fd, "?")
        wait_for(fd, compact, "<still >editable?X")

        # Reverse traversal scrolls the first field back into view. Clicking its
        # frame border focuses the ScrollBox and clears stale Input diagnostics.
        send(fd, "\x1b[Z")
        send(fd, "\x1b[Z")
        send(fd, "\x1b[Z")
        wait_for(fd, compact, "FOCUS  NAME")
        wait_for(fd, compact, "Ada")
        click(fd, col=1, row=6)
        wait_for(fd, compact, "FOCUS  none")
        send(fd, "\t")
        wait_for(fd, compact, "FOCUS  NAME")

        # Traversal wraps in both directions across the retained form boundary.
        send(fd, "\x1b[Z")
        wait_for(fd, compact, "FOCUS  LOCAL EDIT")
        send(fd, "\t")
        wait_for(fd, compact, "FOCUS  NAME")

        send(fd, "\x03")
        status = wait_exit(pid, fd, compact, timeout=2.0)
        if status is None:
            raise AssertionError("input lab did not exit after Ctrl+C")
        assert status == 0, f"exit status {status}"

        print("✓ Cooper Input lab PTY test passed")
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
