#!/usr/bin/env python3
"""Real terminal virtualization: scrolling, jump, nested collapse, and rewrap."""
import os
import signal
from pathlib import Path

from test_cui_controls import Capture
from test_harness import build, drain, resize, send, spawn, wait_exit, wait_for


def main():
    os.chdir(Path(__file__).parent)
    binary = build('cui_virtual_comments')
    pid, fd = spawn(binary, rows=28, cols=100)
    screen = Capture(28, 100)
    try:
        wait_for(fd, screen, 'comment #0')
        drain(fd, screen, 0.2)
        assert '4000 visible' in screen.text()
        screen.save('virtual-initial')
        send(fd, '\x1b[6~')
        drain(fd, screen, 0.2)
        assert 'comment #0 ' not in screen.text(), 'PageDown did not scroll'
        send(fd, 'g')
        wait_for(fd, screen, 'comment #2000')
        screen.save('virtual-jump')
        resize(fd, rows=28, cols=52)
        screen = Capture(28, 52)
        wait_for(fd, screen, 'comment #2000')
        assert 'reading' in screen.text(), 'wrapped comment body missing'
        screen.save('virtual-narrow')
        send(fd, 't')
        wait_for(fd, screen, 'comment #0')
        send(fd, 'e')
        wait_for(fd, screen, '3997 visible')
        wait_for(fd, screen, 'comment #4')
        assert 'comment #1 ' not in screen.text(), 'collapsed descendants still visible'
        screen.save('virtual-collapsed')
        send(fd, 'e')
        wait_for(fd, screen, '4000 visible')
        send(fd, '\x03')
        status = wait_exit(pid, fd, screen)
        assert status is not None and os.waitstatus_to_exitcode(status) == 0
        pid = 0
        print('cui virtual comments PTY test passed')
    finally:
        os.close(fd)
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
                os.waitpid(pid, 0)
            except (ProcessLookupError, ChildProcessError):
                pass


if __name__ == '__main__':
    main()
