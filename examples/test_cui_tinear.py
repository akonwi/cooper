#!/usr/bin/env python3
"""PTY workflow test for the declarative Tinear-inspired example."""

import os
import signal

from test_harness import Screen, binary_path, build, drain, resize, send, spawn, wait_exit, wait_for

ROOT = os.path.dirname(os.path.abspath(__file__))
BIN = binary_path("cui_tinear")


def main():
    os.chdir(ROOT)
    build("cui_tinear")
    pid, fd = spawn(BIN, rows=28, cols=126)
    screen = Screen(28, 126)
    try:
        wait_for(fd, screen, "TINEAR")
        wait_for(fd, screen, "Polish command palette search")

        # Global search traps input and pointer interaction above the board.
        send(fd, "?")
        wait_for(fd, screen, "Search all issues")
        send(fd, "\t\x1b[Z\x1b[<0;13;1M\x1b[<0;13;1m")
        send(fd, "TIN")
        wait_for(fd, screen, "7 results")
        send(fd, "z\r")
        wait_for(fd, screen, "No results.")
        assert "Search all issues" in screen.text(), "Enter opened stale results"
        send(fd, "\x7f" * 4)
        wait_for(fd, screen, "Type an issue title or ID")
        send(fd, "TIN-104")
        wait_for(fd, screen, "1 results")
        send(fd, "\r")
        wait_for(fd, screen, "TIN-104  Document terminal color themes")
        send(fd, "c")
        wait_for(fd, screen, "active: comments")

        # Opening the same result reuses its tab and component state.
        send(fd, "?")
        wait_for(fd, screen, "Search all issues")
        send(fd, "TIN-104")
        wait_for(fd, screen, "1 results")
        row, text = next((i + 1, line) for i, line in enumerate(screen.text().splitlines())
                         if "TIN-104" in line and "Done" in line)
        col = text.index("TIN-104") + 1
        send(fd, f"\x1b[<0;{col};{row}M\x1b[<0;{col};{row}m")
        drain(fd, screen, 0.2)
        assert "Search all issues" not in screen.text()
        assert "active: comments" in screen.text(), "search replaced retained detail state"
        assert screen.text().splitlines()[0].count("TIN-104") == 1

        # Unmounting cancels a pending query; reopening starts empty.
        send(fd, "?")
        wait_for(fd, screen, "Search all issues")
        send(fd, "TIN\x1b")
        drain(fd, screen, 0.7)
        assert "Search all issues" not in screen.text()
        send(fd, "?")
        wait_for(fd, screen, "Type an issue title or ID")
        send(fd, "\x1b")
        drain(fd, screen, 0.15)
        send(fd, "\x1b")
        wait_for(fd, screen, "selected: TIN-142")

        # Inbox selection supersedes a slower initial preview. Scrolling the
        # preview must not move focus away from the notification cursor.
        send(fd, "1")
        wait_for(fd, screen, "Inbox · 3 notifications")
        send(fd, "j")
        wait_for(fd, screen, "Preview: TIN-119")
        drain(fd, screen, 0.6)
        assert "Preview: TIN-142" not in screen.text(), "stale preview won the race"
        send(fd, "?")
        wait_for(fd, screen, "Search all issues")
        send(fd, "themes")
        wait_for(fd, screen, "1 results")
        send(fd, "\x1b")
        drain(fd, screen, 0.15)
        assert "Search all issues" not in screen.text()
        send(fd, " ")
        wait_for(fd, screen, "End of TIN-119 preview")
        send(fd, "j")
        wait_for(fd, screen, "Preview: TIN-104")
        assert "End of TIN-104 preview" not in screen.text(), "selection did not reset preview scroll"
        send(fd, "\r")
        wait_for(fd, screen, "TIN-104  Document terminal color themes")
        send(fd, "\x1b")
        wait_for(fd, screen, "selected: TIN-142")
        send(fd, "1")
        wait_for(fd, screen, "Preview: TIN-104")
        row = next(i for i, line in enumerate(screen.text().splitlines())
                   if "Polish command palette search" in line) + 1
        send(fd, f"\x1b[<0;3;{row}M\x1b[<0;3;{row}m")
        wait_for(fd, screen, "Preview: TIN-142")
        send(fd, "2")
        wait_for(fd, screen, "selected: TIN-142")

        send(fd, "r")
        wait_for(fd, screen, "Refreshing board")
        send(fd, "r")  # Refresh is single-flight.
        wait_for(fd, screen, "Static snapshot 1")
        drain(fd, screen, 0.8)
        assert "Static snapshot 2" not in screen.text()

        # Every transition gets its own frame. Vertical movement stays in a
        # column while horizontal movement preserves the row when possible.
        send(fd, "j")
        wait_for(fd, screen, "selected: TIN-137")
        send(fd, "l")
        wait_for(fd, screen, "selected: TIN-115")
        send(fd, "h")
        wait_for(fd, screen, "selected: TIN-137")
        send(fd, "j")
        wait_for(fd, screen, "selected: TIN-128")
        send(fd, "l")
        wait_for(fd, screen, "selected: TIN-115")  # Clamp row 2 to row 1.
        send(fd, "h")
        wait_for(fd, screen, "selected: TIN-137")
        send(fd, "k")
        wait_for(fd, screen, "selected: TIN-142")
        send(fd, "l")
        wait_for(fd, screen, "selected: TIN-119")
        send(fd, "j")
        wait_for(fd, screen, "selected: TIN-115")
        send(fd, "k")
        wait_for(fd, screen, "selected: TIN-119")
        send(fd, "h")
        wait_for(fd, screen, "selected: TIN-142")
        send(fd, "l")
        wait_for(fd, screen, "selected: TIN-119")
        send(fd, "\r")
        wait_for(fd, screen, "TIN-119  Render board cards without flicker")
        assert any(
            line.strip() == "TIN-119  Render board cards without flicker"
            for line in screen.text().splitlines()
        ), "detail title was not rendered exactly"
        wait_for(fd, screen, "active: description")
        wait_for(fd, screen, "Loading issue details")
        send(fd, "c")
        wait_for(fd, screen, "active: comments")
        wait_for(fd, screen, "Maya  Yesterday  Ready for review.")
        assert "Make the interaction feel immediate" not in screen.text()
        send(fd, "d")
        wait_for(fd, screen, "Make the interaction feel immediate and predictable.")

        # A faster failure supersedes a slow reload; the stale success must
        # not silently replace the error after its old deadline.
        send(fd, "r")
        wait_for(fd, screen, "Loading issue details")
        send(fd, "f")
        wait_for(fd, screen, "Simulated load failed")
        drain(fd, screen, 0.8)
        assert "Simulated load failed" in screen.text()
        send(fd, "r")
        wait_for(fd, screen, "Loading issue details")
        wait_for(fd, screen, "Make the interaction feel immediate and predictable.")
        send(fd, "r")
        wait_for(fd, screen, "Loading issue details")
        send(fd, "\x1b")
        wait_for(fd, screen, "Todo")
        drain(fd, screen, 0.8)
        assert "Make the interaction feel immediate" not in screen.text()
        assert "Loading issue details" not in screen.text()

        # Search remains mounted, Enter accepts it, and the visible result—not
        # the pre-filter selection—is what opens.
        send(fd, "/")
        drain(fd, screen, 0.2)
        send(fd, "themes")
        wait_for(fd, screen, "selected: TIN-104")
        drain(fd, screen, 0.2)
        assert "Document terminal color themes" in screen.text()
        assert "Render board cards without flicker" not in screen.text()
        assert "Polish command palette search" not in screen.text()
        send(fd, "\r")
        wait_for(fd, screen, "selected: TIN-104")
        send(fd, "\r")
        wait_for(fd, screen, "TIN-104  Document terminal color themes")
        assert any(
            line.strip() == "TIN-104  Document terminal color themes"
            for line in screen.text().splitlines()
        ), "filtered result did not open the exact detail title"
        wait_for(fd, screen, "active: description")
        send(fd, "\x1b")
        wait_for(fd, screen, "selected: TIN-104")

        # An accepted empty result set cannot open the old selection.
        send(fd, "/")
        drain(fd, screen, 0.2)
        send(fd, "zzzz-no-match")
        wait_for(fd, screen, "selected: no matches")
        send(fd, "\r")
        wait_for(fd, screen, "selected: no matches")
        send(fd, "\r")
        drain(fd, screen, 0.2)
        assert "active: description" not in screen.text()
        assert "TIN-104  Document terminal color themes" not in screen.text()
        send(fd, "\x1b")
        wait_for(fd, screen, "Polish command palette search")

        # Horizontal movement skips an empty middle column in both directions.
        send(fd, "/")
        drain(fd, screen, 0.2)
        send(fd, "issue")
        wait_for(fd, screen, "selected: TIN-137")
        send(fd, "\r")
        drain(fd, screen, 0.2)
        send(fd, "l")
        wait_for(fd, screen, "selected: TIN-099")
        send(fd, "h")
        wait_for(fd, screen, "selected: TIN-137")
        send(fd, "\x1b")
        wait_for(fd, screen, "selected: TIN-142")

        # Mouse opening and Escape restore the same card's keyboard navigation.
        row = next(i for i, line in enumerate(screen.text().splitlines())
                   if "Keep issue tabs between sessions" in line) + 1
        send(fd, f"\x1b[<0;3;{row}M\x1b[<0;3;{row}m")
        wait_for(fd, screen, "TIN-137  Keep issue tabs between sessions")
        send(fd, "\x1b")
        wait_for(fd, screen, "selected: TIN-137")
        send(fd, "k")
        wait_for(fd, screen, "selected: TIN-142")

        # Switching hides a retained page; closing retires it. Complete a load
        # while hidden, then verify independent sections and keyed tab reuse.
        send(fd, "\r")
        wait_for(fd, screen, "TIN-142  Polish command palette search")
        send(fd, "c")
        wait_for(fd, screen, "active: comments")
        send(fd, "2")
        wait_for(fd, screen, "selected: TIN-142")
        drain(fd, screen, 0.8)
        assert "active: comments" not in screen.text(), "hidden completion stole the screen"
        send(fd, "j")
        wait_for(fd, screen, "selected: TIN-137")
        send(fd, "\r")
        wait_for(fd, screen, "TIN-137  Keep issue tabs between sessions")
        wait_for(fd, screen, "active: description")
        assert screen.line(0).count("TIN-142") == 1
        assert screen.line(0).count("TIN-137") == 1
        send(fd, "\t")  # Last tab wraps to Inbox.
        wait_for(fd, screen, "Inbox · 3 notifications")
        send(fd, "\x1b[Z")  # Shift+Tab wraps back to the last tab.
        wait_for(fd, screen, "TIN-137  Keep issue tabs between sessions")
        send(fd, "\x1b[Z")
        wait_for(fd, screen, "TIN-142  Polish command palette search")
        wait_for(fd, screen, "active: comments")
        wait_for(fd, screen, "Maya  Yesterday  Ready for review.")
        assert "Loading issue details" not in screen.text(), "switching remounted the page"
        send(fd, "\t")
        wait_for(fd, screen, "TIN-137  Keep issue tabs between sessions")
        wait_for(fd, screen, "active: description")
        send(fd, "f")
        wait_for(fd, screen, "Loading issue details")
        send(fd, "2")
        wait_for(fd, screen, "selected: TIN-137")
        drain(fd, screen, 0.4)
        send(fd, "k")
        wait_for(fd, screen, "selected: TIN-142")
        send(fd, "\r")  # Reuses the existing issue tab, not a second instance.
        wait_for(fd, screen, "active: comments")
        assert screen.line(0).count("TIN-142") == 1
        assert "Loading issue details" not in screen.text()

        # Click a tab label, then close it while inactive using its own ×.
        col = screen.line(0).index("TIN-137") + 2
        send(fd, f"\x1b[<0;{col};1M\x1b[<0;{col};1m")
        wait_for(fd, screen, "TIN-137  Keep issue tabs between sessions")
        wait_for(fd, screen, "Simulated load failed")
        send(fd, "\x1b[Z")
        wait_for(fd, screen, "active: comments")
        col = screen.line(0).index("×", screen.line(0).index("TIN-137")) + 1
        send(fd, f"\x1b[<0;{col};1M\x1b[<0;{col};1m")
        drain(fd, screen, 0.2)
        assert "TIN-137" not in screen.line(0), "close button did not remove inactive tab"
        assert "active: comments" in screen.text(), "closing inactive tab changed active page"
        send(fd, "\x1b")
        wait_for(fd, screen, "selected: TIN-142")
        assert "TIN-142" not in screen.line(0)
        send(fd, "\r")
        wait_for(fd, screen, "active: description")
        wait_for(fd, screen, "Loading issue details")
        send(fd, "\x1b")
        wait_for(fd, screen, "selected: TIN-142")

        # Archive all notices, including an empty-list no-op, then refresh.
        # Local refresh must not resurrect archived static notifications.
        send(fd, "1")
        wait_for(fd, screen, "Inbox · 3 notifications")
        send(fd, "\x7f")
        wait_for(fd, screen, "Inbox · 2 notifications")
        wait_for(fd, screen, "Preview: TIN-119")
        send(fd, "\x7f")
        wait_for(fd, screen, "Inbox · 1 notifications")
        wait_for(fd, screen, "Preview: TIN-104")
        send(fd, "\x7f")
        wait_for(fd, screen, "You're all caught up.")
        send(fd, "\x7f\r")
        drain(fd, screen, 0.2)
        assert "No notifications to preview." in screen.text()
        send(fd, "r")
        wait_for(fd, screen, "Refreshing inbox")
        send(fd, "r")
        wait_for(fd, screen, "Inbox · 0 notifications")
        assert "You're all caught up." in screen.text()
        send(fd, "2")
        wait_for(fd, screen, "selected: TIN-142")

        resize(fd, rows=12, cols=100)
        compact = Screen(12, 100)
        wait_for(fd, compact, "TINEAR")
        wait_for(fd, compact, "selected: TIN-142")
        send(fd, "j")
        wait_for(fd, compact, "selected: TIN-137")
        send(fd, "j")
        wait_for(fd, compact, "selected: TIN-128")
        wait_for(fd, compact, "Add keyboard shortcut reference")
        wait_for(fd, compact, "Backlog · Desktop")
        send(fd, "l")
        wait_for(fd, compact, "selected: TIN-115")
        send(fd, "l")
        wait_for(fd, compact, "selected: TIN-099")
        wait_for(fd, compact, "Ship compact issue detail layout")
        wait_for(fd, compact, "Cycle 17 · Desktop")
        send(fd, "?")
        wait_for(fd, compact, "Search all issues")
        send(fd, "TIN")
        wait_for(fd, compact, "7 results")
        for _ in range(6):
            send(fd, "\x1b[B")
            drain(fd, compact, 0.05)
        wait_for(fd, compact, "Ship compact issue detail layout")
        send(fd, "\x1b[A")
        drain(fd, compact, 0.05)
        send(fd, "\r")
        wait_for(fd, compact, "TIN-104  Document terminal color themes")
        send(fd, "\x03")
        status = wait_exit(pid, fd, compact)
        assert status is not None, "Tinear example did not exit on Ctrl+C"
        assert os.waitstatus_to_exitcode(status) == 0
    finally:
        try: os.close(fd)
        except OSError: pass
        try:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
        except (ProcessLookupError, ChildProcessError): pass
    print("cui tinear PTY test passed")


if __name__ == "__main__":
    main()
