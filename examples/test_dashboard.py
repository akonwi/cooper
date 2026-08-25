#!/usr/bin/env python3
"""PTY validation for Cooper's live operations dashboard."""

import os
import re
import signal
import sys
import time

from test_harness import Screen, binary_path, build, drain, read_for, resize, send, spawn, wait_exit, wait_for

ROOT = os.path.dirname(os.path.abspath(__file__))
BIN = binary_path("dashboard")


def state_line(screen):
    return next(line for line in screen.text().splitlines() if "State:" in line)


def state_value(screen, label):
    match = re.search(rf"{label}: (\d+)", state_line(screen))
    if not match:
        raise AssertionError(f"missing {label!r} in dashboard state\n{screen.text()}")
    return int(match.group(1))


def request_count(screen):
    match = re.search(r"REQUESTS\s+(\d+) total", screen.text())
    if not match:
        raise AssertionError(f"missing request count\n{screen.text()}")
    return int(match.group(1))


def visible_sequences(screen):
    return [int(value) for value in re.findall(r"\[(\d+)\] ", screen.text())]


def wait_for_tick(fd, screen, minimum, timeout=3.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        read_for(fd, screen, 0.05)
        try:
            if state_value(screen, "Tick") >= minimum:
                return state_value(screen, "Tick")
        except (StopIteration, AssertionError):
            pass
    raise AssertionError(f"dashboard did not reach tick {minimum}\n{screen.text()}")


def main():
    os.chdir(ROOT)
    build("dashboard")
    pid, fd = spawn(BIN, rows=24, cols=90)
    screen = Screen(24, 90)
    try:
        wait_for_tick(fd, screen, 1)
        drain(fd, screen, 0.1)

        # The first dispatched sample updates every retained dashboard region.
        initial = screen.text()
        for expected in (
            "COOPER OPERATIONS",
            "CPU",
            "MEMORY",
            "NETWORK",
            "LATENCY",
            "SYSTEM PULSE",
            "CPU HISTORY",
            "REQUESTS",
            "EVENT STREAM",
            "Follow: ON",
        ):
            assert expected in initial, f"missing dashboard region {expected!r}"

        # Pausing is UI-owned: the background timer keeps dispatching, but no
        # metric or tick state changes while paused.
        send(fd, " ")
        wait_for(fd, screen, "State: PAUSED")
        paused_tick = state_value(screen, "Tick")
        paused_rows = state_value(screen, "Rows")
        paused_requests = request_count(screen)
        drain(fd, screen, 0.75)
        assert state_value(screen, "Tick") == paused_tick, "dashboard advanced while paused"
        assert request_count(screen) == paused_requests, "metrics changed while paused"

        # Manual events append through the same bounded retained log and remain
        # visible because its requested scroll offset follows the bottom.
        send(fd, "a")
        wait_for(fd, screen, "MANUAL")
        wait_for(fd, screen, f"Rows: {paused_rows + 1}")
        assert "operator checkpoint" in screen.text(), "manual event row was not visible"

        send(fd, "f")
        wait_for(fd, screen, "Follow: OFF")

        # Fill the bounded log, then cross its cap. Evicting rows above a
        # follow-disabled viewport must preserve the same logical first row.
        rows_to_cap = 60 - state_value(screen, "Rows")
        sequence_at_cap = state_value(screen, "Seq") + rows_to_cap
        send(fd, "a" * rows_to_cap)
        wait_for(fd, screen, f"Seq: {sequence_at_cap}")
        drain(fd, screen, 0.2)
        first_visible = visible_sequences(screen)[0]

        send(fd, "aaa")
        wait_for(fd, screen, f"Seq: {sequence_at_cap + 3}")
        drain(fd, screen, 0.2)
        assert state_value(screen, "Rows") == 60, "bounded event stream exceeded its cap"
        assert visible_sequences(screen)[0] == first_visible, "cap eviction moved a follow-disabled viewport"

        # End restores a persistent bottom request. A shorter viewport must
        # still reveal the latest event after layout recomputes its maximum.
        send(fd, "\x1b[F")
        wait_for(fd, screen, "Follow: ON")
        latest = sequence_at_cap + 3
        wait_for(fd, screen, f"[{latest}] MANUAL")
        resize(fd, rows=20, cols=70)
        compact = Screen(20, 70)
        wait_for(fd, compact, "State: PAUSED")
        wait_for(fd, compact, f"[{latest}] MANUAL")
        drain(fd, compact, 0.2)
        assert compact.line(19).endswith("┘"), "dashboard footer overwrote its border"

        # Restore the full layout, clear every retained row, and verify that a
        # resumed dispatch advances both tick and chart telemetry.
        resize(fd, rows=24, cols=90)
        screen = Screen(24, 90)
        wait_for(fd, screen, "State: PAUSED")
        send(fd, "c")
        wait_for(fd, screen, "Rows: 0")
        assert "MANUAL" not in screen.text(), "cleared event row remained visible"

        send(fd, " ")
        wait_for(fd, screen, "State: RUNNING")
        wait_for_tick(fd, screen, paused_tick + 1)
        assert request_count(screen) > paused_requests, "dispatched metrics did not advance after resume"

        # A narrow layout clips content inside panels while retaining chart
        # rows and the live status footer.
        resize(fd, rows=24, cols=70)
        narrow = Screen(24, 70)
        wait_for(fd, narrow, "State: RUNNING")
        drain(fd, narrow, 0.2)
        assert "WORKERS" in narrow.text(), "chart rows disappeared after resize"
        assert narrow.line(23).endswith("┘"), "dashboard footer overwrote its border"

        send(fd, "q")
        status = wait_exit(pid, fd, narrow, timeout=2.0)
        if status is None:
            raise AssertionError("dashboard did not exit after Q")
        assert status == 0, f"exit status {status}"

        print("✓ Cooper dashboard PTY test passed")
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
