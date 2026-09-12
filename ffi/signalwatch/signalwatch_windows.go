//go:build windows

package signalwatch

import "os"

func New() *Watcher {
	return newWatcher(os.Interrupt)
}

func classify(received os.Signal) Event {
	return Event{Kind: Shutdown}
}
