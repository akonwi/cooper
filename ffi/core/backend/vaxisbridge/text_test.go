package vaxisbridge

import "testing"

func TestValidHyperlink(t *testing.T) {
	valid := []string{
		"",
		"https://example.com/path?q=你好",
		"file:///tmp/report",
	}
	for _, value := range valid {
		if !ValidHyperlink(value) {
			t.Fatalf("expected valid hyperlink %q", value)
		}
	}

	invalid := []string{
		"line\nbreak",
		"escape\x1b\\",
		"bell\a",
		"delete\x7f",
		"c1\u009c",
		string([]byte{0x9c}),
	}
	for _, value := range invalid {
		if ValidHyperlink(value) {
			t.Fatalf("expected invalid hyperlink bytes %q", []byte(value))
		}
	}
}
