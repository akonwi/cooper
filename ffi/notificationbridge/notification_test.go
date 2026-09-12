package notificationbridge

import (
	"sync"
	"testing"
)

type notificationCall struct {
	title string
	body  string
}

type fakeTerminal struct {
	mu    sync.Mutex
	id    string
	calls []notificationCall
}

func (f *fakeTerminal) TerminalID() string { return f.id }

func (f *fakeTerminal) Notify(title, body string) {
	f.mu.Lock()
	f.calls = append(f.calls, notificationCall{title: title, body: body})
	f.mu.Unlock()
}

func environment(values map[string]string) func(string) string {
	return func(name string) string { return values[name] }
}

func TestOSC777NotificationPreservesLogicalTitleAndSanitizesFields(t *testing.T) {
	terminal := &fakeTerminal{id: "ghostty 1.2.3"}
	backend := newBackend(terminal, environment(nil))

	if !backend.Notify("build;done\nnow\x1b", "Cooper; CI") {
		t.Fatal("expected supported notification")
	}
	if len(terminal.calls) != 1 {
		t.Fatalf("calls = %d, want 1", len(terminal.calls))
	}
	if got, want := terminal.calls[0], (notificationCall{title: "Cooper  CI", body: "build done now "}); got != want {
		t.Fatalf("call = %#v, want %#v", got, want)
	}
}

func TestOSC777TitlelessNotificationForcesOSC777(t *testing.T) {
	terminal := &fakeTerminal{id: "WezTerm 20240203"}
	backend := newBackend(terminal, environment(nil))

	if !backend.Notify("finished", "") {
		t.Fatal("expected supported notification")
	}
	if got, want := terminal.calls[0], (notificationCall{title: "finished", body: ""}); got != want {
		t.Fatalf("call = %#v, want %#v", got, want)
	}
}

func TestOSC9CombinesTitleAndMessage(t *testing.T) {
	terminal := &fakeTerminal{id: "iTerm2 3.5"}
	backend := newBackend(terminal, environment(nil))

	if !backend.Notify("tests;passed\u009d"+string([]byte{0xff}), "Cooper") {
		t.Fatal("expected supported notification")
	}
	if got, want := terminal.calls[0], (notificationCall{title: "", body: "Cooper: tests passed  "}); got != want {
		t.Fatalf("call = %#v, want %#v", got, want)
	}
}

func TestGhosttyProgressReportsUseFixedOSC9Payloads(t *testing.T) {
	terminal := &fakeTerminal{id: "ghostty 1.2.3"}
	backend := newBackend(terminal, environment(nil))

	requests := []struct {
		state      int
		percent    int
		hasPercent bool
		body       string
	}{
		{state: 0, body: "4;0"},
		{state: 1, percent: 42, hasPercent: true, body: "4;1;42"},
		{state: 2, body: "4;2"},
		{state: 2, percent: 75, hasPercent: true, body: "4;2;75"},
		{state: 3, body: "4;3"},
		{state: 4, body: "4;4"},
		{state: 4, percent: 25, hasPercent: true, body: "4;4;25"},
	}
	for _, request := range requests {
		if !backend.SetProgress(request.state, request.percent, request.hasPercent) {
			t.Fatalf("progress request %#v was rejected", request)
		}
	}
	if len(terminal.calls) != len(requests) {
		t.Fatalf("calls = %d, want %d", len(terminal.calls), len(requests))
	}
	for index, request := range requests {
		if got, want := terminal.calls[index], (notificationCall{title: "", body: request.body}); got != want {
			t.Fatalf("call %d = %#v, want %#v", index, got, want)
		}
	}
}

func TestProgressSupportIsGhosttyOnlyAndMultiplexerSafe(t *testing.T) {
	tests := []struct {
		name      string
		id        string
		env       map[string]string
		supported bool
	}{
		{name: "terminal id", id: "ghostty 1.2.3", supported: true},
		{name: "term program", env: map[string]string{"TERM_PROGRAM": "ghostty"}, supported: true},
		{name: "term", env: map[string]string{"TERM": "xterm-ghostty"}, supported: true},
		{name: "forced", env: map[string]string{"COOPER_TERMINAL_PROGRESS": "1"}, supported: true},
		{name: "disabled", id: "ghostty", env: map[string]string{"COOPER_TERMINAL_PROGRESS": "off"}},
		{name: "tmux", id: "ghostty", env: map[string]string{"TMUX": "/tmp/tmux"}},
		{name: "other terminal", id: "WezTerm 20240203"},
		{name: "identity overrides stale environment", id: "iTerm2 3.5", env: map[string]string{"TERM_PROGRAM": "ghostty"}},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			terminal := &fakeTerminal{id: test.id}
			backend := newBackend(terminal, environment(test.env))
			if got := backend.SetProgress(3, 0, false); got != test.supported {
				t.Fatalf("supported = %t, want %t", got, test.supported)
			}
		})
	}
}

func TestProgressRejectsInvalidStateAndPercentCombinations(t *testing.T) {
	terminal := &fakeTerminal{id: "ghostty"}
	backend := newBackend(terminal, environment(nil))
	for _, request := range []struct {
		state      int
		percent    int
		hasPercent bool
	}{
		{state: -1},
		{state: 5},
		{state: 0, percent: 1, hasPercent: true},
		{state: 1},
		{state: 1, percent: 101, hasPercent: true},
		{state: 3, percent: 1, hasPercent: true},
	} {
		if backend.SetProgress(request.state, request.percent, request.hasPercent) {
			t.Fatalf("invalid progress request %#v was accepted", request)
		}
	}
	if len(terminal.calls) != 0 {
		t.Fatal("invalid progress request reached terminal")
	}
}

func TestEnvironmentSelectionAndOverrides(t *testing.T) {
	tests := []struct {
		name     string
		id       string
		env      map[string]string
		expected protocol
	}{
		{name: "term program", env: map[string]string{"TERM_PROGRAM": "ghostty"}, expected: protocolOSC777},
		{name: "windows terminal", env: map[string]string{"WT_SESSION": "session"}, expected: protocolOSC777},
		{name: "term features", env: map[string]string{"TERM_FEATURES": "CwNo"}, expected: protocolOSC9},
		{name: "forced osc9", id: "ghostty", env: map[string]string{"COOPER_NOTIFICATION_PROTOCOL": "OSC9"}, expected: protocolOSC9},
		{name: "disabled", id: "ghostty", env: map[string]string{"COOPER_NOTIFICATIONS": "off"}, expected: protocolNone},
		{name: "forced unsupported osc99", id: "ghostty", env: map[string]string{"COOPER_NOTIFICATION_PROTOCOL": "osc99"}, expected: protocolOSC99},
		{name: "kitty unsupported", id: "kitty 0.40", expected: protocolOSC99},
		{name: "conemu overloads osc9", id: "ConEmu 230724", expected: protocolNone},
		{name: "unknown", id: "xterm", expected: protocolNone},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			terminal := &fakeTerminal{id: test.id}
			backend := newBackend(terminal, environment(test.env))
			if backend.protocol != test.expected {
				t.Fatalf("protocol = %d, want %d", backend.protocol, test.expected)
			}
		})
	}
}

func TestMultiplexersRemainUnsupported(t *testing.T) {
	for _, env := range []map[string]string{
		{"TMUX": "/tmp/tmux", "TERM_PROGRAM": "ghostty"},
		{"STY": "123.screen", "TERM_PROGRAM": "iTerm.app"},
		{"ZELLIJ_SESSION_NAME": "session", "TERM_PROGRAM": "ghostty"},
	} {
		terminal := &fakeTerminal{id: ""}
		backend := newBackend(terminal, environment(env))
		if backend.Notify("message", "title") {
			t.Fatalf("expected multiplexer environment %#v to be unsupported", env)
		}
		if len(terminal.calls) != 0 {
			t.Fatal("unsupported notification reached terminal")
		}
	}
}
