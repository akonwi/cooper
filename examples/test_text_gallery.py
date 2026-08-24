#!/usr/bin/env python3
"""PTY validation for Cooper's interactive text gallery."""

import os
import signal
import sys

from test_harness import Screen, binary_path, build, drain, resize, send, spawn, wait_exit, wait_for

ROOT = os.path.dirname(os.path.abspath(__file__))
BIN = binary_path("text_gallery")


def find_text(screen, needle):
    for row, line in enumerate(screen.text().splitlines()):
        if needle in line:
            return row, line.index(needle)
    raise AssertionError(f"did not find {needle!r}\n{screen.text()}")


def wrap_regions(screen):
    lines = screen.text().splitlines()
    row = next(index for index, line in enumerate(lines) if "┌─ WORD" in line)
    header = lines[row]
    word = header.index("┌─ WORD")
    character = header.index("┌─ CHAR")
    none = header.index("┌─ NONE")
    content = lines[row + 1]
    return content[word:character], content[character:none], content[none:]


def character_source(screen):
    lines = screen.text().splitlines()
    row = next(index for index, line in enumerate(lines) if "┌─ WORD" in line)
    header = lines[row]
    character = header.index("┌─ CHAR")
    none = header.index("┌─ NONE")
    parts = []
    for offset in range(1, 5):
        segment = lines[row + offset][character:none].replace("│", "")
        parts.append("".join(segment.split()))
    return "".join(parts)


def click(fd, col, row):
    send(fd, f"\x1b[<0;{col + 1};{row + 1}M")
    send(fd, f"\x1b[<0;{col + 1};{row + 1}m")


def choose(fd, screen, key, title):
    send(fd, key)
    wait_for(fd, screen, title)
    drain(fd, screen, 0.15)


def main():
    os.chdir(ROOT)
    build("text_gallery")
    pid, fd = spawn(BIN, rows=24, cols=80)
    screen = Screen(24, 80)
    try:
        wait_for(fd, screen, "SAMPLE 1/3 · ELLIPSIS")
        drain(fd, screen, 0.2)

        # The initial sheet exposes attributes, rich spans, Unicode and all
        # three wrapping modes without corrupting its surrounding borders.
        initial = screen.text()
        for expected in (
            "STYLE SPECIMENS",
            "BOLD",
            "DIM",
            "ITALIC",
            "UNDERLINE",
            "BLINK",
            "REVERSE",
            "STRIKE",
            "HIDDEN",
            "FG + BG",
            "WORD",
            "CHAR",
            "NONE",
            "GRAPHEMES",
            "你好世界",
            "READY",
            "WARN",
            "ERROR",
            "Cooper source",
        ):
            assert expected in initial, f"missing gallery specimen {expected!r}"
        word_region, character_region, none_region = wrap_regions(screen)
        assert "Text wraps" in word_region, "word-wrapped sample was not rendered"
        assert "Text wraps c" in character_region, "character wrapping did not split the next word"
        assert "…" in none_region, "NONE card did not paint its targeted ellipsis"

        # Text selection uses the gallery's custom selection style and reports
        # the logical selected word through App.on_selection_change.
        row, col = find_text(screen, "confident")
        click(fd, col + 2, row)
        click(fd, col + 2, row)
        wait_for(fd, screen, "Selection: confident")
        send(fd, "c")
        wait_for(fd, screen, "Selection: none")

        # Linked spans can be intercepted without launching an external app.
        row, col = find_text(screen, "Cooper source")
        click(fd, col + 2, row)
        wait_for(fd, screen, "Link intercepted: https://github.com/akonwi/cooper")

        # Complete content replacement preserves the three retained Text
        # controls and demonstrates long-token and Unicode wrapping.
        choose(fd, screen, "2", "SAMPLE 2/3 · ELLIPSIS")
        assert "supercalifra" in screen.text(), "long-token sample was not rendered"
        # Complex grapheme cell geometry is covered by Cooper's deterministic
        # headless tests; this minimal PTY emulator only verifies the mode swap.
        choose(fd, screen, "3", "SAMPLE 3/3 · ELLIPSIS")
        choose(fd, screen, " ", "SAMPLE 1/3 · ELLIPSIS")

        # Overflow changes from ellipsis to clipping and back in place.
        choose(fd, screen, "e", "SAMPLE 1/3 · CLIP")
        _, _, none_region = wrap_regions(screen)
        assert "…" not in none_region, "NONE card retained its ellipsis after switching to clipping"
        choose(fd, screen, "e", "SAMPLE 1/3 · ELLIPSIS")
        _, _, none_region = wrap_regions(screen)
        assert "…" in none_region, "NONE card did not restore its ellipsis"

        # Clipped content remains inside panel borders in a narrower viewport.
        resize(fd, rows=24, cols=70)
        narrow = Screen(24, 70)
        wait_for(fd, narrow, "SAMPLE 1/3 · ELLIPSIS")
        drain(fd, narrow, 0.2)
        specimen_header, _ = find_text(narrow, "STYLE SPECIMENS")
        specimen_right = narrow.line(specimen_header).index("╮")
        badge_row, _ = find_text(narrow, "FG + BG")
        assert narrow.line(badge_row)[specimen_right] == "│", "specimen content overwrote its right border"
        assert character_source(narrow) == "Textwrapscleanlyacrossterminal.", "narrow character wrap dropped source text"
        assert narrow.line(23).endswith("┘"), "footer content overwrote its border"

        resize(fd, rows=20, cols=80)
        compact = Screen(20, 80)
        wait_for(fd, compact, "SAMPLE 1/3 · ELLIPSIS")
        drain(fd, compact, 0.2)
        specimen_bottom = next(line for line in compact.text().splitlines() if line.startswith("╰"))
        assert "FG + BG" not in specimen_bottom, "specimen content overwrote its bottom border"
        assert compact.line(19).endswith("┘"), "compact footer overwrote its border"

        send(fd, "q")
        status = wait_exit(pid, fd, compact, timeout=2.0)
        if status is None:
            raise AssertionError("text gallery did not exit after Q")
        assert status == 0, f"exit status {status}"

        print("✓ Cooper text gallery PTY test passed")
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
