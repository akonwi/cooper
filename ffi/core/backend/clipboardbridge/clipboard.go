package clipboardbridge

import (
	"context"
	"sync"

	"go.rockorager.dev/vaxis"
)

// Backend adapts Vaxis's OSC 52 clipboard operations to a cancellable App
// lifetime. Cooper owns operation ordering and concurrent-read policy in Ard.
type Backend struct {
	terminal *vaxis.Vaxis

	mu      sync.Mutex
	ctx     context.Context
	cancel  context.CancelFunc
	stopped bool
}

// New creates a clipboard backend bound to terminal.
func New(terminal *vaxis.Vaxis) *Backend {
	ctx, cancel := context.WithCancel(context.Background())
	return &Backend{terminal: terminal, ctx: ctx, cancel: cancel}
}

// Read requests the terminal host's clipboard and blocks until it responds or
// the current active lifetime is cancelled.
func (b *Backend) Read() (string, error) {
	b.mu.Lock()
	ctx := b.ctx
	stopped := b.stopped
	b.mu.Unlock()
	if stopped {
		return "", context.Canceled
	}
	if err := ctx.Err(); err != nil {
		return "", err
	}
	return b.terminal.ClipboardPop(ctx)
}

// Write emits an OSC 52 clipboard write. Vaxis exposes no acknowledgement or
// output error for this operation.
func (b *Backend) Write(value string) {
	b.terminal.ClipboardPush(value)
}

// Suspend cancels reads before Vaxis releases terminal input.
func (b *Backend) Suspend() {
	b.mu.Lock()
	b.cancel()
	b.mu.Unlock()
}

// Resume creates a fresh read lifetime after Vaxis reacquires terminal input.
func (b *Backend) Resume() {
	b.mu.Lock()
	if !b.stopped {
		b.ctx, b.cancel = context.WithCancel(context.Background())
	}
	b.mu.Unlock()
}

// Cancel permanently unblocks reads. It is safe to call repeatedly.
func (b *Backend) Cancel() {
	b.mu.Lock()
	if !b.stopped {
		b.stopped = true
		b.cancel()
	}
	b.mu.Unlock()
}
