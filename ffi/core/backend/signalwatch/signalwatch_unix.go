//go:build darwin || freebsd || linux || netbsd || openbsd

package signalwatch

import (
	"os"
	"syscall"

	"golang.org/x/term"
)

func New() *Watcher {
	return newWatcher(
		os.Interrupt,
		syscall.SIGHUP,
		syscall.SIGQUIT,
		syscall.SIGTERM,
		syscall.SIGWINCH,
	)
}

func classify(received os.Signal) Event {
	if received == syscall.SIGWINCH {
		cols, rows := terminalSize()
		return Event{Kind: Resize, Cols: cols, Rows: rows}
	}
	return Event{Kind: Shutdown}
}

func terminalSize() (int, int) {
	for _, file := range []*os.File{os.Stdout, os.Stdin, os.Stderr} {
		if cols, rows, err := term.GetSize(int(file.Fd())); err == nil {
			return cols, rows
		}
	}
	if tty, err := os.Open("/dev/tty"); err == nil {
		defer tty.Close()
		if cols, rows, err := term.GetSize(int(tty.Fd())); err == nil {
			return cols, rows
		}
	}
	return 0, 0
}
