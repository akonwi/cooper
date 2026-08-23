package urlopen

import (
	"fmt"
	"os/exec"
	"runtime"
	"strings"
)

// Open starts the platform's default URL/file handler without invoking a shell.
func Open(target string) error {
	cmd, err := platformCommand(runtime.GOOS, target)
	if err != nil {
		return err
	}
	if err := cmd.Start(); err != nil {
		return err
	}
	go func() {
		_ = cmd.Wait()
	}()
	return nil
}

func platformCommand(goos, target string) (*exec.Cmd, error) {
	if target == "" {
		return nil, fmt.Errorf("cannot open an empty link")
	}
	// Prevent a relative target from being interpreted as an opener option.
	if strings.HasPrefix(target, "-") {
		return nil, fmt.Errorf("cannot open a link beginning with '-'")
	}

	switch goos {
	case "darwin":
		return exec.Command("/usr/bin/open", target), nil
	case "linux", "freebsd", "openbsd", "netbsd", "dragonfly":
		return exec.Command("xdg-open", target), nil
	case "windows":
		return exec.Command("rundll32", "url.dll,FileProtocolHandler", target), nil
	default:
		return nil, fmt.Errorf("opening links is unsupported on %s", goos)
	}
}
