#!/usr/bin/env python3
"""Real HTTP + PTY integration test; no public network dependency."""
import collections
import json
import os
import signal
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from test_harness import Screen, binary_path, build, drain, resize, send, spawn, wait_exit, wait_for

COMMENTS = int(os.environ.get('HN_STRESS_COMMENTS', '100'))


class API(BaseHTTPRequestHandler):
    counts = collections.Counter()
    lock = threading.Lock()
    active = 0
    peak = 0

    def log_message(self, *args):
        pass

    def do_GET(self):
        with self.lock:
            API.counts[self.path] += 1
            attempt = API.counts[self.path]
            API.active += 1
            API.peak = max(API.peak, API.active)
        try:
            status = 200
            value = None
            payload = None
            time.sleep(0.025)
            if self.path == '/topstories.json':
                value = [1, 2, 3]
            elif self.path == '/newstories.json':
                time.sleep(0.7)
                value = [4]
            elif self.path == '/askstories.json':
                if attempt == 1:
                    status = 503
                else:
                    value = [3]
            elif self.path == '/showstories.json':
                value = []
            elif self.path.startswith('/item/'):
                id = int(self.path.split('/')[-1].split('.')[0])
                value = dict(id=id, by=f'user-{id}', kids=[], text=f'Comment {id}: thoughtful discussion.')
                if id < 5:
                    value.update(title=f'Story {id}: terminals &amp; components', score=123,
                                 url='https://example.com/article', descendants=123, text='',
                                 kids=list(range(100, 120)) if id == 1 else [5000])
                    if id in (2, 3):
                        time.sleep(0.1)
                elif id == 100:
                    value.update(by='parent-author', kids=list(range(200, 200 + COMMENTS)),
                                 text='Parent &lt;literal&gt; &amp; Unicode café 界.<p>'
                                      'A long paragraph about retained components and asynchronous requests. ' * 3)
                elif id == 101:
                    value = dict(id=id, deleted=True, kids=[4000])
                elif id == 102 and attempt == 1:
                    status = 500
                elif id == 102 and attempt == 2:
                    payload = b'{invalid json'
                elif id == 102 and attempt == 3:
                    value = None
                elif id == 103:
                    value = dict(id=id, dead=True)
                elif id == 200:
                    value.update(by='nested-author', text='Nested reply with <i>emphasis</i>.')
                elif id == 4000:
                    value.update(text='Reply survives deleted parent.')
                elif id == 5000:
                    time.sleep(0.7)
                    value.update(kids=[5001], text='Late response must not reopen reader.')
                elif id == 199 + COMMENTS:
                    value.update(kids=[6000])
                elif 6000 <= id < 6012:
                    value.update(kids=[id + 1] if id < 6011 else [], text=f'Deep reply {id}.')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(payload if payload is not None else json.dumps(value).encode())
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            with self.lock:
                API.active -= 1


class Capture(Screen):
    def __init__(self, rows, cols):
        super().__init__(rows, cols)
        self.raw = b''

    def feed(self, data):
        self.raw += data
        super().feed(data)

    def save(self, name):
        destination = os.environ.get('HN_CAPTURE_DIR')
        if destination:
            os.makedirs(destination, exist_ok=True)
            with open(os.path.join(destination, name + '.json'), 'w') as file:
                json.dump(dict(rows=self.rows, cols=self.cols,
                               ansi=self.raw.decode('utf8', errors='replace')), file)


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    build('cui_hackernews')
    server = ThreadingHTTPServer(('127.0.0.1', 0), API)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    pid, fd = spawn(binary_path('cui_hackernews'), rows=30, cols=110,
                    env={'HN_API_ROOT': f'http://127.0.0.1:{server.server_port}'})
    screen = Capture(30, 110)
    try:
        wait_for(fd, screen, '3 loaded · 0 requests')
        assert 'Story 1: terminals & components' in screen.text()
        assert screen.text().index('Story 1:') < screen.text().index('Story 2:') < screen.text().index('Story 3:')
        screen.save('feed')
        started = time.monotonic()
        send(fd, '\r')
        wait_for(fd, screen, '29 loaded · 0 requests')
        print(f'Initial 30-item batch (one injected failure): {time.monotonic() - started:.3f}s')
        wait_for(fd, screen, 'Nested reply with emphasis.')
        assert 'Parent <literal> & Unicode café' in screen.text()
        assert '<p>' not in screen.text()
        screen.save('reader')
        send(fd, 'j\r')  # Collapse the parent, not the story.
        wait_for(fd, screen, 'parent-author (collapsed)')
        assert 'Nested reply' not in screen.text()
        assert '[deleted]' in screen.text()
        assert '[dead]' in screen.text()
        assert 'HTTP 500' in screen.text()
        screen.save('collapsed')
        send(fd, 'r')
        wait_for(fd, screen, 'Invalid JSON')
        send(fd, 'r')
        wait_for(fd, screen, 'Item 102 is unavailable')
        send(fd, 'r')
        wait_for(fd, screen, '30 loaded · 0 requests')
        assert API.counts['/item/102.json'] == 4
        with API.lock:
            before = sum(API.counts.values())
        send(fd, '\r')
        wait_for(fd, screen, 'Nested reply with emphasis.')
        with API.lock:
            assert sum(API.counts.values()) == before, 'expansion refetched cached items'
        total = COMMENTS + 34
        load_started = time.monotonic()
        send(fd, 'm' * ((total + 29) // 30))
        wait_for(fd, screen, f'{total} loaded · 0 requests', timeout=60)
        print(f'Remaining {total - 30} items: {time.monotonic() - load_started:.3f}s; peak HTTP concurrency={API.peak}')
        assert 1 < API.peak <= 6
        assert API.counts['/item/6011.json'] == 1, 'deep descendants were not loaded'
        memory = f'/proc/{pid}/status'
        if os.path.exists(memory):
            with open(memory) as file:
                print(next(line.strip() for line in file if line.startswith('VmRSS:')))

        # Selection navigation must remain usable with the larger retained tree.
        resize(fd, rows=18, cols=72)
        compact = Capture(18, 72)
        wait_for(fd, compact, 'HACKER NEWS')
        navigation_started = time.monotonic()
        for _ in range(12):
            send(fd, 'j')
            drain(fd, compact, 0.04)
        wait_for(fd, compact, 'Comment 211:')
        print(f'12 navigation keys including 40ms pacing: {time.monotonic() - navigation_started:.3f}s')
        compact.save('compact')
        send(fd, ' ')
        wait_for(fd, compact, 'Comment 216:')
        send(fd, '\x1b[5~')  # PageUp scrolls without changing selection.
        wait_for(fd, compact, 'Comment 211:')
        send(fd, '\x1b')
        wait_for(fd, compact, '3 loaded · 0 requests')
        send(fd, 'j\r')
        wait_for(fd, compact, '1 loaded · 1 requests')
        send(fd, '\x1b')
        wait_for(fd, compact, '3 loaded · 0 requests')
        drain(fd, compact, 0.9)
        assert API.counts['/item/5001.json'] == 0, 'unmounted reader scheduled more work'
        assert 'Late response' not in compact.text()
        send(fd, '2')
        wait_for(fd, compact, 'Loading new stories')
        send(fd, '3')
        wait_for(fd, compact, 'HTTP 503')
        compact.save('feed-error')
        send(fd, 'r')
        wait_for(fd, compact, 'Story 3:')
        drain(fd, compact, 0.8)
        assert API.counts['/item/4.json'] == 0, 'stale feed completion scheduled items'
        send(fd, '4')
        wait_for(fd, compact, 'No stories.')
        compact.save('empty')
        send(fd, '\x03')
        status = wait_exit(pid, fd, compact)
        assert status is not None and os.waitstatus_to_exitcode(status) == 0
    finally:
        os.close(fd)
        try:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
        except (ProcessLookupError, ChildProcessError):
            pass
        server.shutdown()
        server.server_close()
        thread.join()
    print('cui Hacker News HTTP/PTY test passed')


if __name__ == '__main__':
    main()
