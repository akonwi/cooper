#!/usr/bin/env python3
"""CUI Select, TabSelect, and TextArea interaction and rendering smoke test."""
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
        directory = os.environ.get('CUI_CAPTURE_DIR')
        if directory:
            path = Path(directory)
            path.mkdir(parents=True, exist_ok=True)
            (path / f'{name}.json').write_text(json.dumps({
                'rows': self.rows, 'cols': self.cols,
                'ansi': self.ansi.decode('utf-8', errors='replace'),
            }))


def click_text(fd, screen, text):
    for y, line in enumerate(screen.text().splitlines(), 1):
        if text in line:
            x = line.index(text) + 1
            send(fd, f'\x1b[<0;{x};{y}M\x1b[<0;{x};{y}m')
            return
    raise AssertionError(f'{text} missing from screen')


def main():
    os.chdir(Path(__file__).parent)
    build('cui_controls')
    pid, fd = spawn(binary_path('cui_controls'), rows=26, cols=72)
    screen = Capture(26, 72)
    try:
        wait_for(fd, screen, 'CUI · Issue editor')
        screen.save('initial')
        send(fd, '\x1b[C')
        wait_for(fd, screen, 'highlight=Activity')
        assert 'section=0' in screen.text(), 'highlight committed without Enter'
        send(fd, '\r')
        wait_for(fd, screen, 'section=1')
        click_text(fd, screen, 'Overview')
        wait_for(fd, screen, 'section=0')
        click_text(fd, screen, 'Activity')
        wait_for(fd, screen, 'section=1')
        send(fd, '\t')
        drain(fd, screen, 0.1)
        send(fd, '\r')
        wait_for(fd, screen, 'When there is time')
        send(fd, '\x1b[B\x1b[B')
        wait_for(fd, screen, 'highlight=High')
        assert 'Needs attention soon' in screen.text(), 'rerender closed the popup'
        screen.save('open-menu')
        send(fd, '\r')
        wait_for(fd, screen, 'priority=2')
        send(fd, '\t')
        drain(fd, screen, 0.1)
        send(fd, '\rEdited note')
        wait_for(fd, screen, 'Edited note')
        send(fd, '\x1bOR')  # F3 reorders the keyed editor and priority field.
        drain(fd, screen, 0.15)
        send(fd, '!')
        wait_for(fd, screen, 'Edited note!')
        send(fd, '\x1bOQ')
        wait_for(fd, screen, 'reject edits: true')
        send(fd, 'REJECTED')
        drain(fd, screen, 0.15)
        assert 'REJECTED' not in screen.text()
        assert 'Edited note!' in screen.text()
        screen.save('editing')
        resize(fd, rows=26, cols=48)
        screen = Capture(26, 48)
        wait_for(fd, screen, 'Edited note!')
        screen.save('compact')
        send(fd, '\x1bOS')  # F4 clears selection and text through props.
        wait_for(fd, screen, 'Write a multiline note')
        assert 'Choose priority' in screen.text()
        screen.save('empty')
        click_text(fd, screen, 'Choose priority')
        wait_for(fd, screen, 'Plan for this cycle')
        click_text(fd, screen, 'Plan for this cycle')
        wait_for(fd, screen, 'priority=1')
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
    print('cui controls PTY test passed')


if __name__ == '__main__':
    main()
