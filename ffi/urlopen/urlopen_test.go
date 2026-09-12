package urlopen

import "testing"

func TestPlatformCommandPassesTargetWithoutShell(t *testing.T) {
	target := "https://example.com/a path?x=$(touch nope)&y='quoted'"
	tests := []struct {
		goos string
		want []string
	}{
		{goos: "darwin", want: []string{"/usr/bin/open", target}},
		{goos: "linux", want: []string{"xdg-open", target}},
		{goos: "windows", want: []string{"rundll32", "url.dll,FileProtocolHandler", target}},
	}
	for _, test := range tests {
		t.Run(test.goos, func(t *testing.T) {
			cmd, err := platformCommand(test.goos, target)
			if err != nil {
				t.Fatal(err)
			}
			if len(cmd.Args) != len(test.want) {
				t.Fatalf("args = %#v, want %#v", cmd.Args, test.want)
			}
			for i := range test.want {
				if cmd.Args[i] != test.want[i] {
					t.Fatalf("arg %d = %q, want %q", i, cmd.Args[i], test.want[i])
				}
			}
		})
	}
}

func TestPlatformCommandRejectsUnsafeOrUnsupportedTargets(t *testing.T) {
	for _, test := range []struct {
		goos   string
		target string
	}{
		{goos: "linux", target: ""},
		{goos: "linux", target: "--help"},
		{goos: "plan9", target: "https://example.com"},
	} {
		if _, err := platformCommand(test.goos, test.target); err == nil {
			t.Fatalf("platformCommand(%q, %q) succeeded", test.goos, test.target)
		}
	}
}
