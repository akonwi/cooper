package signalwatch

import (
	"os"
	"os/signal"
	"sync"
)

type Kind int

const (
	None Kind = iota
	Resize
	Shutdown
)

type Event struct {
	Kind Kind
	Cols int
	Rows int
}

type Watcher struct {
	events  chan bool
	signals chan os.Signal
	done    chan struct{}
	once    sync.Once
	mu      sync.Mutex
	resize  Event
	stop    bool
}

func newWatcher(watched ...os.Signal) *Watcher {
	w := &Watcher{
		events:  make(chan bool, 1),
		signals: make(chan os.Signal, 8),
		done:    make(chan struct{}),
	}
	signal.Notify(w.signals, watched...)
	go w.run()
	return w
}

func (w *Watcher) Events() <-chan bool { return w.events }

// Next returns one pending event. Shutdown takes priority over the latest
// coalesced resize. A zero Kind means no event remains.
func (w *Watcher) Next() Event {
	w.mu.Lock()
	defer w.mu.Unlock()
	if w.stop {
		w.stop = false
		return Event{Kind: Shutdown}
	}
	if w.resize.Kind == Resize {
		event := w.resize
		w.resize = Event{}
		return event
	}
	return Event{}
}

func (w *Watcher) Close() {
	w.once.Do(func() {
		signal.Stop(w.signals)
		close(w.done)
	})
}

func (w *Watcher) run() {
	defer close(w.events)
	for {
		select {
		case received := <-w.signals:
			event := classify(received)
			w.mu.Lock()
			if event.Kind == Shutdown {
				w.stop = true
			} else if event.Kind == Resize {
				w.resize = event
			}
			w.mu.Unlock()
			select {
			case w.events <- true:
			default:
			}
		case <-w.done:
			return
		}
	}
}
