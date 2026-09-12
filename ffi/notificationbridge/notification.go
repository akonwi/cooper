package notificationbridge

import (
	"os"
	"strconv"
	"strings"
	"sync"
	"unicode/utf8"

	"go.rockorager.dev/vaxis"
)

type protocol uint8

const (
	protocolNone protocol = iota
	protocolOSC9
	protocolOSC777
	protocolOSC99
)

type terminal interface {
	TerminalID() string
	Notify(title, body string)
}

// Backend selects the notification protocol that Vaxis can currently emit.
// It deliberately reports OSC 99-only terminals and multiplexers as
// unsupported until Vaxis owns those protocol and passthrough details.
type Backend struct {
	mu                sync.Mutex
	terminal          terminal
	protocol          protocol
	progressSupported bool
}

// New creates a notification backend bound to terminal.
func New(terminal *vaxis.Vaxis) *Backend {
	return newBackend(terminal, os.Getenv)
}

func newBackend(terminal terminal, getenv func(string) string) *Backend {
	return &Backend{
		terminal:          terminal,
		protocol:          selectProtocol(terminal.TerminalID(), getenv),
		progressSupported: supportsProgress(terminal.TerminalID(), getenv),
	}
}

// Notify sanitizes malformed UTF-8 and terminal control fields, then emits one
// terminal-mediated desktop notification.
// True means an emission protocol was selected and Vaxis was invoked; it does
// not confirm that the terminal or desktop displayed the notification.
func (b *Backend) Notify(message, title string) bool {
	b.mu.Lock()
	defer b.mu.Unlock()

	switch b.protocol {
	case protocolOSC9:
		message = sanitize(message, true)
		title = sanitize(title, true)
		if title != "" {
			message = title + ": " + message
		}
		b.terminal.Notify("", message)
		return true
	case protocolOSC777:
		message = sanitize(message, true)
		title = sanitize(title, true)
		if title == "" {
			// Vaxis chooses OSC 9 for an empty title. Putting the message in
			// OSC 777's first field emits the same titleless form as OpenTUI.
			if message == "" {
				message = " "
			}
			b.terminal.Notify(message, "")
		} else {
			b.terminal.Notify(title, message)
		}
		return true
	default:
		return false
	}
}

// SetProgress emits an OSC 9;4 terminal progress report. States correspond to
// remove, normal, error, indeterminate, and paused. The payload consists only
// of validated numeric fields selected by Cooper.
func (b *Backend) SetProgress(state, percent int, hasPercent bool) bool {
	b.mu.Lock()
	defer b.mu.Unlock()
	if !b.progressSupported || percent < 0 || percent > 100 {
		return false
	}

	var payload string
	switch state {
	case 0:
		if hasPercent {
			return false
		}
		payload = "4;0"
	case 1:
		if !hasPercent {
			return false
		}
		payload = "4;1;" + strconv.Itoa(percent)
	case 2:
		payload = "4;2"
	case 3:
		if hasPercent {
			return false
		}
		payload = "4;3"
	case 4:
		payload = "4;4"
	default:
		return false
	}
	if hasPercent && (state == 2 || state == 4) {
		payload += ";" + strconv.Itoa(percent)
	}
	b.terminal.Notify("", payload)
	return true
}

func selectProtocol(terminalID string, getenv func(string) string) protocol {
	if disabled(getenv("COOPER_NOTIFICATIONS")) || inMultiplexer(terminalID, getenv) {
		return protocolNone
	}

	switch strings.ToLower(strings.TrimSpace(getenv("COOPER_NOTIFICATION_PROTOCOL"))) {
	case "osc9":
		return protocolOSC9
	case "osc777":
		return protocolOSC777
	case "osc99":
		return protocolOSC99
	case "none", "0", "false", "off":
		return protocolNone
	}

	if selected := detectProtocol(terminalID); selected != protocolNone {
		return selected
	}
	if termFeaturesHasCode(getenv("TERM_FEATURES"), "No") {
		return protocolOSC9
	}
	if selected := detectProtocol(getenv("TERM_PROGRAM")); selected != protocolNone {
		return selected
	}
	if getenv("WT_SESSION") != "" {
		return protocolOSC777
	}
	return detectProtocol(getenv("TERM"))
}

func disabled(value string) bool {
	switch strings.ToLower(strings.TrimSpace(value)) {
	case "0", "false", "off":
		return true
	default:
		return false
	}
}

func supportsProgress(terminalID string, getenv func(string) string) bool {
	if disabled(getenv("COOPER_TERMINAL_PROGRESS")) || inMultiplexer(terminalID, getenv) {
		return false
	}
	switch strings.ToLower(strings.TrimSpace(getenv("COOPER_TERMINAL_PROGRESS"))) {
	case "1", "true", "on":
		return true
	}
	identifier := strings.ToLower(strings.TrimSpace(terminalID))
	if identifier != "" {
		return strings.HasPrefix(identifier, "ghostty")
	}
	return strings.EqualFold(strings.TrimSpace(getenv("TERM_PROGRAM")), "ghostty") ||
		strings.Contains(strings.ToLower(getenv("TERM")), "ghostty")
}

func inMultiplexer(terminalID string, getenv func(string) string) bool {
	identifier := strings.ToLower(strings.TrimSpace(terminalID))
	if strings.HasPrefix(identifier, "tmux") || strings.HasPrefix(identifier, "screen") || strings.HasPrefix(identifier, "zellij") {
		return true
	}
	term := strings.ToLower(getenv("TERM"))
	return getenv("TMUX") != "" ||
		getenv("STY") != "" ||
		getenv("ZELLIJ") != "" ||
		getenv("ZELLIJ_SESSION_NAME") != "" ||
		getenv("ZELLIJ_PANE_ID") != "" ||
		strings.HasPrefix(term, "tmux") ||
		strings.HasPrefix(term, "screen")
}

func detectProtocol(value string) protocol {
	value = strings.ToLower(value)
	if value == "" {
		return protocolNone
	}

	// Kitty and foot require OSC 99, which Vaxis does not yet expose. Keep
	// that positive identification so weaker environment hints cannot replace it.
	if strings.Contains(value, "kitty") || strings.Contains(value, "foot") {
		return protocolOSC99
	}

	for _, name := range []string{
		"ghostty", "wezterm", "warp", "hterm", "blink", "contour",
		"vte", "gnome", "tilix", "terminator", "xfce", "urxvt",
		"rxvt", "windows terminal", "windows_terminal",
	} {
		if strings.Contains(value, name) {
			return protocolOSC777
		}
	}

	for _, name := range []string{"iterm", "apple_terminal", "terminal.app"} {
		if strings.Contains(value, name) {
			return protocolOSC9
		}
	}
	return protocolNone
}

func termFeaturesHasCode(features, code string) bool {
	for i := 0; i < len(features); {
		if features[i] < 'A' || features[i] > 'Z' {
			i++
			continue
		}
		start := i
		i++
		for i < len(features) && features[i] >= 'a' && features[i] <= 'z' {
			i++
		}
		if features[start:i] == code {
			return true
		}
		for i < len(features) && features[i] >= '0' && features[i] <= '9' {
			i++
		}
	}
	return false
}

func sanitize(value string, replaceSemicolon bool) string {
	var output strings.Builder
	output.Grow(len(value))
	for len(value) > 0 {
		current, size := utf8.DecodeRuneInString(value)
		if current == utf8.RuneError && size == 1 {
			output.WriteByte(' ')
			value = value[1:]
			continue
		}
		if current < 0x20 || (current >= 0x7f && current <= 0x9f) || (replaceSemicolon && current == ';') {
			output.WriteByte(' ')
		} else {
			output.WriteRune(current)
		}
		value = value[size:]
	}
	return output.String()
}
