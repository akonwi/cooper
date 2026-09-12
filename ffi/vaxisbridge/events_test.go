package vaxisbridge

import (
	"sync"
	"testing"

	vaxis "go.rockorager.dev/vaxis"
)

func TestPasteBufferAggregatesAndResets(t *testing.T) {
	buffer := NewPasteBuffer()
	buffer.Start()
	buffer.AppendKey(vaxis.Key{Text: "one", EventType: vaxis.EventPaste})
	buffer.AppendKey(vaxis.Key{Keycode: 'j', Modifiers: vaxis.ModCtrl, EventType: vaxis.EventPaste})
	buffer.AppendKey(vaxis.Key{Text: "two", EventType: vaxis.EventPaste})
	if got := buffer.Finish(); !got.Active || got.Value != "one\ntwo" {
		t.Fatalf("Finish() = %#v, want active %q", got, "one\ntwo")
	}
	if got := buffer.Finish(); got.Active || got.Value != "" {
		t.Fatalf("second Finish() = %#v, want inactive", got)
	}
}

func TestPasteBufferSerializesConcurrentAppends(t *testing.T) {
	buffer := NewPasteBuffer()
	buffer.Start()
	var wg sync.WaitGroup
	for range 32 {
		wg.Add(1)
		go func() {
			defer wg.Done()
			buffer.AppendKey(vaxis.Key{Text: "x", EventType: vaxis.EventPaste})
		}()
	}
	wg.Wait()
	got := buffer.Finish()
	if !got.Active || len(got.Value) != 32 {
		t.Fatalf("Finish() = %#v, want 32 serialized bytes", got)
	}
}

func TestPasteTextPreservesTextNewlinesAndTabs(t *testing.T) {
	tests := []struct {
		name string
		key  vaxis.Key
		want string
	}{
		{name: "printable", key: vaxis.Key{Text: "界", EventType: vaxis.EventPaste}, want: "界"},
		{name: "carriage return", key: vaxis.Key{Keycode: vaxis.KeyEnter, EventType: vaxis.EventPaste}, want: "\r"},
		{name: "line feed", key: vaxis.Key{Keycode: 'j', Modifiers: vaxis.ModCtrl, EventType: vaxis.EventPaste}, want: "\n"},
		{name: "tab", key: vaxis.Key{Keycode: vaxis.KeyTab, EventType: vaxis.EventPaste}, want: "\t"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := PasteText(tt.key); got != tt.want {
				t.Fatalf("PasteText() = %q, want %q", got, tt.want)
			}
		})
	}
}
