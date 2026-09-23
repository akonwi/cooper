package fixtures_test

import (
	"fmt"
	"html"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"

	vaxis "github.com/akonwi/vaxis"
	"github.com/akonwi/vaxis/widgets/term"
)

func screenApp(t *testing.T, mode string, rows, height int) (*term.Model, <-chan error) {
	t.Helper()
	binary := os.Getenv("COOPER_SCREEN_BINARY")
	if binary == "" {
		t.Skip("run python3 test_screen_modes.py to build the Ard fixture")
	}
	vt := term.New()
	vt.Focus()
	closed := make(chan error, 1)
	vt.Attach(func(event vaxis.Event) {
		if event, ok := event.(term.EventClosed); ok {
			closed <- event.Error
		}
	})
	cmd := exec.Command("sh", "-c", `printf 'shell prefix\npartial output'; exec "$COOPER_SCREEN_BINARY"`)
	cmd.Env = append(os.Environ(), "COOPER_SCREEN_MODE="+mode, fmt.Sprintf("COOPER_SCREEN_HEIGHT=%d", height))
	if err := vt.StartWithSize(cmd, 48, rows); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(vt.Close)
	return vt, closed
}

func waitScreen(t *testing.T, vt *term.Model, text string) int {
	t.Helper()
	deadline := time.Now().Add(5 * time.Second)
	for time.Now().Before(deadline) {
		for row, line := range vt.Rows() {
			if strings.Contains(line, text) {
				return row
			}
		}
		time.Sleep(time.Millisecond)
	}
	t.Fatalf("missing %q in screen: %q", text, vt.Rows())
	return -1
}

// Export actual emulator cells; this is a readable PTY capture, not a mock UI.
func captureScreen(t *testing.T, vt *term.Model, name string) {
	t.Helper()
	dir := os.Getenv("COOPER_SCREEN_CAPTURE_DIR")
	if dir == "" {
		return
	}
	rows := vt.Rows()
	var svg strings.Builder
	fmt.Fprintf(&svg, `<svg xmlns="http://www.w3.org/2000/svg" width="640" height="%d"><rect width="100%%" height="100%%" fill="#17202c"/>`, len(rows)*26+32)
	for row, line := range rows {
		fmt.Fprintf(&svg, `<text x="16" y="%d" fill="#edf3fa" font-family="DejaVu Sans Mono" font-size="18" xml:space="preserve">%s</text>`, 36+row*26, html.EscapeString(line))
	}
	svg.WriteString("</svg>")
	if err := os.WriteFile(filepath.Join(dir, name+".svg"), []byte(svg.String()), 0o644); err != nil {
		t.Fatal(err)
	}
}

func key(vt *term.Model, code rune, control bool) {
	var modifiers vaxis.ModifierMask
	if control {
		modifiers = vaxis.ModCtrl
	}
	vt.Update(vaxis.Key{Keycode: code, Text: string(code), Modifiers: modifiers})
}

func waitCursor(t *testing.T, vt *term.Model, row, col int) {
	t.Helper()
	deadline := time.Now().Add(5 * time.Second)
	for time.Now().Before(deadline) {
		at := vt.Snapshot()
		if at.CursorVisible && at.CursorRow == row && at.CursorCol == col {
			return
		}
		time.Sleep(time.Millisecond)
	}
	t.Fatalf("cursor did not reach (%d,%d): %+v", col, row, vt.Snapshot())
}

func quitScreen(t *testing.T, vt *term.Model, closed <-chan error) {
	t.Helper()
	vt.Update(vaxis.Key{Keycode: vaxis.KeyEsc})
	select {
	case err := <-closed:
		if err != nil {
			t.Fatal(err)
		}
	case <-time.After(5 * time.Second):
		t.Fatalf("application did not exit: %q", vt.Rows())
	}
	// Println's trailing newline scrolls the marker into history on a one-row terminal.
	if len(vt.Rows()) == 1 {
		vt.Update(vaxis.Key{Keycode: vaxis.KeyPgUp, Modifiers: vaxis.ModShift})
	}
	waitScreen(t, vt, "SHELL RESTORED")
}

func TestScreenModes(t *testing.T) {
	for _, mode := range []string{"alt", "main", "inline", "split"} {
		t.Run(mode, func(t *testing.T) {
			vt, closed := screenApp(t, mode, 8, 4)
			origin := waitScreen(t, vt, "SCREEN READY")
			if mode == "inline" || mode == "split" {
				if origin != 2 || !strings.HasPrefix(vt.RowString(0), "shell prefix") || !strings.HasPrefix(vt.RowString(1), "partial output") {
					t.Fatalf("preceding shell output changed: %q", vt.Rows())
				}
			} else if origin != 0 {
				t.Fatalf("full-height origin=%d", origin)
			}
			captureScreen(t, vt, mode+"-initial")
			// Editing exercises cursor placement and repeated frame updates at
			// nonzero origins, not just an initial hidden-cursor paint.
			waitCursor(t, vt, origin+1, 7)
			key(vt, 'Z', false)
			waitScreen(t, vt, "edit meZ")
			vt.Update(vaxis.Mouse{Button: vaxis.MouseLeftButton, Row: origin + 1, Col: 1, EventType: vaxis.EventPress})
			vt.Update(vaxis.Mouse{Button: vaxis.MouseLeftButton, Row: origin + 1, Col: 1, EventType: vaxis.EventRelease})
			waitCursor(t, vt, origin+1, 1)
			key(vt, 'Q', false)
			waitScreen(t, vt, "eQdit meZ")
			key(vt, 'o', true)
			if mode == "inline" || mode == "split" {
				for i := 2; i <= 10; i++ {
					waitScreen(t, vt, fmt.Sprintf("OUTPUT %d", i-1))
					key(vt, 'o', true)
				}
				if origin := waitScreen(t, vt, "OUTPUT 10"); origin != 4 {
					t.Fatalf("bounded surface origin=%d, want 4; %q", origin, vt.Rows())
				}
				if !strings.HasPrefix(vt.RowString(3), "output 10") {
					t.Fatalf("missing appended output above UI: %q", vt.Rows())
				}
			} else {
				waitScreen(t, vt, "OUTPUT UNAVAILABLE")
			}
			captureScreen(t, vt, mode+"-output")
			key(vt, 's', true)
			waitScreen(t, vt, "RESUMED")
			waitScreen(t, vt, "eQdit meZ")
			quitScreen(t, vt, closed)
			if mode == "split" || mode == "main" {
				for _, row := range vt.Rows() {
					if strings.Contains(row, "RESUMED") || strings.Contains(row, "eQdit meZ") {
						t.Fatalf("clear-on-exit left UI cells: %q", vt.Rows())
					}
				}
			}
			if mode != "alt" {
				for i := 0; i < 30; i++ {
					vt.Update(vaxis.Key{Keycode: vaxis.KeyPgUp, Modifiers: vaxis.ModShift})
				}
				if !strings.HasPrefix(vt.RowString(0), "shell prefix") || !strings.HasPrefix(vt.RowString(1), "partial output") {
					t.Fatalf("original shell output missing from history: %q", vt.Rows())
				}
			}
			if mode == "inline" || mode == "split" {
				// With the child exited, expand the emulator to inspect all history.
				vt.Resize(48, 80)
				counts := map[string]int{}
				for _, row := range vt.Rows() {
					counts[strings.TrimSpace(row)]++
				}
				for i := 1; i <= 10; i++ {
					if counts[fmt.Sprintf("output %d", i)] != 1 {
						t.Fatalf("output %d missing or duplicated in history: %q", i, vt.Rows())
					}
				}
				if counts["final output"] != 1 || counts["external output"] != 1 {
					t.Fatalf("release lost accepted or external output: %q", vt.Rows())
				}
				preserved := 0
				if mode == "inline" {
					preserved = 2 // intentional snapshots at suspend and final release
				}
				if counts["eQdit meZ"] != preserved || counts["SCREEN READY"] != 0 {
					t.Fatalf("UI frames leaked into output history: %q", vt.Rows())
				}
			}
		})
	}
}

func TestScreenResizeAndFullHeightFooter(t *testing.T) {
	for _, mode := range []string{"inline", "split"} {
		t.Run(mode, func(t *testing.T) {
			vt, closed := screenApp(t, mode, 10, 6)
			waitScreen(t, vt, "SCREEN READY")
			waitCursor(t, vt, 3, 7)
			vt.Resize(24, 4)
			waitCursor(t, vt, 1, 7)
			key(vt, 'o', true)
			waitScreen(t, vt, "OUTPUT 1")
			vt.Resize(48, 12)
			for i := 2; i <= 14; i++ {
				key(vt, 'o', true)
				waitScreen(t, vt, fmt.Sprintf("OUTPUT %d", i))
			}
			if origin := waitScreen(t, vt, "OUTPUT 14"); origin != 6 {
				t.Fatalf("requested height was not restored after clamp: origin=%d; %q", origin, vt.Rows())
			}
			quitScreen(t, vt, closed)
		})
	}
	for _, rows := range []int{1, 2, 4} {
		t.Run(fmt.Sprintf("tiny-%d", rows), func(t *testing.T) {
			vt, closed := screenApp(t, "split", rows, rows)
			waitScreen(t, vt, "SCREEN READY")
			key(vt, 'o', true)
			waitScreen(t, vt, "OUTPUT 1")
			quitScreen(t, vt, closed)
			for i := 0; i < 30; i++ {
				vt.Update(vaxis.Key{Keycode: vaxis.KeyPgUp, Modifiers: vaxis.ModShift})
			}
			if !strings.HasPrefix(vt.RowString(0), "shell prefix") {
				t.Fatalf("tiny footer lost shell history: %q", vt.Rows())
			}
		})
	}
}
