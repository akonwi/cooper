package signalwatch

import (
	"os"
	"testing"
	"time"
)

func TestInterruptRequestsShutdown(t *testing.T) {
	if got := classify(os.Interrupt).Kind; got != Shutdown {
		t.Fatalf("classify interrupt = %v, want shutdown", got)
	}
}

func TestNextPrioritizesShutdownAndCoalescesResize(t *testing.T) {
	w := &Watcher{
		resize: Event{Kind: Resize, Cols: 120, Rows: 40},
		stop:   true,
	}
	if got := w.Next(); got.Kind != Shutdown {
		t.Fatalf("first event = %+v, want shutdown", got)
	}
	if got := w.Next(); got.Kind != Resize || got.Cols != 120 || got.Rows != 40 {
		t.Fatalf("second event = %+v, want latest resize", got)
	}
	if got := w.Next(); got.Kind != None {
		t.Fatalf("final event = %+v, want none", got)
	}
}

func TestWatcherCloseIsIdempotent(t *testing.T) {
	w := &Watcher{
		events:  make(chan bool, 1),
		signals: make(chan os.Signal, 1),
		done:    make(chan struct{}),
	}
	go w.run()
	w.Close()
	w.Close()

	select {
	case _, ok := <-w.Events():
		if ok {
			t.Fatal("watcher events remained open")
		}
	case <-time.After(time.Second):
		t.Fatal("watcher did not stop")
	}
}
