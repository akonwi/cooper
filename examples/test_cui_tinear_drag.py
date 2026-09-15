#!/usr/bin/env python3
"""Physical pointer regression tests for CUI board drag/drop."""
import json
import os
import signal
from pathlib import Path

from test_harness import Screen, binary_path, build, drain, resize, send, spawn, wait_exit, wait_for


class Capture(Screen):
    def __init__(self, rows, cols):
        super().__init__(rows, cols)
        self.ansi = bytearray()

    def feed(self, data):
        self.ansi.extend(data)
        super().feed(data)

    def save(self, name):
        directory = os.environ.get('TINEAR_CAPTURE_DIR')
        if directory:
            path = Path(directory)
            path.mkdir(parents=True, exist_ok=True)
            (path / f'{name}.json').write_text(json.dumps({
                'rows': self.rows, 'cols': self.cols,
                'ansi': self.ansi.decode('utf-8', errors='replace'),
            }))


def mouse(fd, code, x, y, release=False):
    send(fd, f'\x1b[<{code};{x};{y}{"m" if release else "M"}')


def card(screen, identifier):
    for y, line in enumerate(screen.text().splitlines()[4:-1], 5):
        if identifier in line:
            return line.index(identifier) + 1, y
    raise AssertionError(f'{identifier} missing:\n{screen.text()}')


def main():
    os.chdir(Path(__file__).parent)
    build('cui_tinear')
    pid, fd = spawn(binary_path('cui_tinear'), rows=28, cols=126)
    screen = Capture(28, 126)
    try:
        wait_for(fd, screen, 'Polish command palette search')
        x, y = card(screen, 'TIN-142')
        # One-cell jitter is still a click, not a move.
        mouse(fd, 0, x, y)
        mouse(fd, 32, x + 1, y)
        mouse(fd, 0, x + 1, y, True)
        wait_for(fd, screen, 'TIN-142  Polish command palette search')
        send(fd, '\x1b')
        wait_for(fd, screen, 'selected: TIN-142')
        x, y = card(screen, 'TIN-142')

        # Same-column and outside-board releases never move or open a card.
        for target_x, target_y in [(x + 3, y), (60, 2)]:
            mouse(fd, 0, x, y)
            mouse(fd, 32, target_x, target_y)
            wait_for(fd, screen, '↳')
            mouse(fd, 0, target_x, target_y, True)
            drain(fd, screen, 0.15)
            assert 'drop on a column' not in screen.text()
            assert 'active: description' not in screen.text()
            assert card(screen, 'TIN-142')[0] < 39

        # Escape cancels even if the eventual release is over a valid destination.
        mouse(fd, 0, x, y)
        mouse(fd, 32, 55, y + 2)
        wait_for(fd, screen, 'drop on a column')
        screen.save('dragging')
        send(fd, '\x1b')
        drain(fd, screen, 0.1)
        mouse(fd, 0, 55, y + 2, True)
        drain(fd, screen, 0.1)
        assert 'drop on a column' not in screen.text()
        assert card(screen, 'TIN-142')[0] < 39

        # Focus loss cancels ownership; a later release cannot commit the move.
        mouse(fd, 0, x, y)
        drain(fd, screen, 0.05)
        mouse(fd, 32, 55, y + 2)
        wait_for(fd, screen, 'drop on a column')
        send(fd, '\x1b[O')
        drain(fd, screen, 0.1)
        send(fd, '\x1b[I')
        mouse(fd, 0, 55, y + 2, True)
        drain(fd, screen, 0.1)
        assert 'drop on a column' not in screen.text()
        assert card(screen, 'TIN-142')[0] < 39

        # Cross-column move appends, retains selection, and does not open a tab.
        mouse(fd, 0, x, y)
        mouse(fd, 32, 55, y + 2)
        wait_for(fd, screen, 'drop on a column')
        mouse(fd, 0, 55, y + 2, True)
        for frame in range(14):
            drain(fd, screen, 0.025)
            screen.save(f'animation-{frame:02}')
        wait_for(fd, screen, 'Todo  2')
        wait_for(fd, screen, 'In Progress  3')
        assert 40 < card(screen, 'TIN-142')[0] < 79
        assert card(screen, 'TIN-142')[1] > card(screen, 'TIN-115')[1]
        assert 'selected: TIN-142' in screen.text()
        assert 'active: description' not in screen.text()
        wait_for(fd, screen, 'Moved TIN-142 to In Progress')
        screen.save('moved')
        drain(fd, screen, 3.1)
        assert 'Moved TIN-142' not in screen.text(), 'toast did not expire'
        send(fd, '\r')
        wait_for(fd, screen, 'TIN-142  Polish command palette search')
        assert 'In Progress' in screen.text(), 'detail retained the old workflow state'
        send(fd, '\x1b')
        wait_for(fd, screen, 'selected: TIN-142')
        resize(fd, rows=18, cols=100)
        screen = Capture(18, 100)
        wait_for(fd, screen, 'selected: TIN-142')
        x, y = card(screen, 'TIN-142')
        mouse(fd, 0, x, y)
        drain(fd, screen, 0.05)
        mouse(fd, 32, 90, 6)
        wait_for(fd, screen, 'drop on a column')
        before_scroll = card(screen, 'TIN-115')[0]
        mouse(fd, 69, 90, 6)  # Shift+wheel down, through the ghost.
        drain(fd, screen, 0.1)
        assert card(screen, 'TIN-115')[0] < before_scroll, 'ghost blocked horizontal scrolling'
        screen.save('compact-drag')
        mouse(fd, 0, 90, 6, True)
        wait_for(fd, screen, 'Moved TIN-142 to Done')
        drain(fd, screen, 0.3)
        assert 'selected: TIN-142' in screen.text()
        screen.save('compact-moved')
        send(fd, '\x03')
        status = wait_exit(pid, fd, screen)
        assert status is not None and os.waitstatus_to_exitcode(status) == 0
    finally:
        os.close(fd)
        try:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
        except (ProcessLookupError, ChildProcessError):
            pass
    print('cui tinear drag PTY test passed')


if __name__ == '__main__':
    main()
