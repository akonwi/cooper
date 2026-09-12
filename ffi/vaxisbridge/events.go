package vaxisbridge

import (
	"strings"
	"sync"

	vaxis "go.rockorager.dev/vaxis"
)

type KeyData struct {
	Name      string
	Text      string
	EventType int
	Shift     bool
	Ctrl      bool
	Alt       bool
	Super     bool
}

// PasteText preserves line feeds and tabs that Vaxis reports with empty
// Key.Text while bracketed paste is active.
func PasteText(key vaxis.Key) string {
	if key.Text != "" {
		return key.Text
	}
	switch key.Keycode {
	case vaxis.KeyEnter:
		return "\r"
	case vaxis.KeyTab:
		return "\t"
	case vaxis.KeySpace:
		return " "
	case 'j':
		if key.Modifiers&vaxis.ModCtrl != 0 {
			return "\n"
		}
	}
	return ""
}

type PasteResult struct {
	Value  string
	Active bool
}

type PasteBuffer struct {
	mu     sync.Mutex
	value  strings.Builder
	active bool
}

func NewPasteBuffer() *PasteBuffer { return &PasteBuffer{} }

func (b *PasteBuffer) Start() {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.value.Reset()
	b.active = true
}

func (b *PasteBuffer) AppendKey(key vaxis.Key) bool {
	b.mu.Lock()
	defer b.mu.Unlock()
	if b.active {
		b.value.WriteString(PasteText(key))
	}
	return b.active
}

func (b *PasteBuffer) Finish() PasteResult {
	b.mu.Lock()
	defer b.mu.Unlock()
	if !b.active {
		return PasteResult{}
	}
	result := PasteResult{Value: b.value.String(), Active: true}
	b.value.Reset()
	b.active = false
	return result
}

func (b *PasteBuffer) Reset() {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.value.Reset()
	b.active = false
}

func Key(key vaxis.Key) KeyData {
	name := ""
	switch key.Keycode {
	case vaxis.KeyEnter:
		name = "return"
	case vaxis.KeyEsc:
		name = "escape"
	case vaxis.KeyTab:
		name = "tab"
	case vaxis.KeySpace:
		name = "space"
	case vaxis.KeyBackspace:
		name = "backspace"
	case vaxis.KeyPgUp:
		name = "page_up"
	case vaxis.KeyPgDown:
		name = "page_down"
	default:
		normalized := key
		normalized.Modifiers = 0
		normalized.EventType = vaxis.EventPress
		name = strings.ToLower(normalized.String())
	}

	eventType := 0
	switch key.EventType {
	case vaxis.EventRepeat:
		eventType = 1
	case vaxis.EventRelease:
		eventType = 2
	}

	return KeyData{
		Name:      name,
		Text:      key.Text,
		EventType: eventType,
		Shift:     key.Modifiers&vaxis.ModShift != 0,
		Ctrl:      key.Modifiers&vaxis.ModCtrl != 0,
		Alt:       key.Modifiers&vaxis.ModAlt != 0,
		Super:     key.Modifiers&vaxis.ModSuper != 0,
	}
}

type MouseData struct {
	EventType int
	Button    int
	X         int
	Y         int
	Shift     bool
	Ctrl      bool
	Alt       bool
	Super     bool
	ScrollX   int
	ScrollY   int
}

func Mouse(mouse vaxis.Mouse) MouseData {
	data := MouseData{
		X:     mouse.Col,
		Y:     mouse.Row,
		Shift: mouse.Modifiers&vaxis.ModShift != 0,
		Ctrl:  mouse.Modifiers&vaxis.ModCtrl != 0,
		Alt:   mouse.Modifiers&vaxis.ModAlt != 0,
		Super: mouse.Modifiers&vaxis.ModSuper != 0,
	}

	switch mouse.Button {
	case vaxis.MouseLeftButton:
		data.Button = 1
	case vaxis.MouseMiddleButton:
		data.Button = 2
	case vaxis.MouseRightButton:
		data.Button = 3
	case vaxis.MouseWheelUp:
		data.EventType = 8
		data.ScrollY = -1
	case vaxis.MouseWheelDown:
		data.EventType = 8
		data.ScrollY = 1
	case vaxis.MouseWheelLeft:
		data.EventType = 8
		data.ScrollX = -1
	case vaxis.MouseWheelRight:
		data.EventType = 8
		data.ScrollX = 1
	}

	if data.EventType != 8 {
		switch mouse.EventType {
		case vaxis.EventRelease:
			data.EventType = 1
		case vaxis.EventMotion:
			if data.Button == 0 {
				data.EventType = 2
			} else {
				data.EventType = 3
			}
		default:
			data.EventType = 0
		}
	}
	return data
}
