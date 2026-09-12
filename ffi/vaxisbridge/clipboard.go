package vaxisbridge

import (
	"context"
	"sync"

	"go.rockorager.dev/vaxis"
)

// Clipboard adapts Vaxis's OSC 52 clipboard operations to a cancellable App
// lifetime. Cooper owns operation ordering and concurrent-read policy in Ard.
type Clipboard struct {
	terminal *vaxis.Vaxis

	mu      sync.Mutex
	ctx     context.Context
	cancel  context.CancelFunc
	stopped bool
}

// NewClipboard creates a clipboard adapter bound to terminal.
func NewClipboard(terminal *vaxis.Vaxis) *Clipboard {
	ctx, cancel := context.WithCancel(context.Background())
	return &Clipboard{terminal: terminal, ctx: ctx, cancel: cancel}
}

// Read requests the terminal host's clipboard and blocks until it responds or
// the current active lifetime is cancelled.
func (b *Clipboard) Read() (string, error) {
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
func (b *Clipboard) Write(value string) {
	b.terminal.ClipboardPush(value)
}

// Suspend cancels reads before Vaxis releases terminal input.
func (b *Clipboard) Suspend() {
	b.mu.Lock()
	b.cancel()
	b.mu.Unlock()
}

// Resume creates a fresh read lifetime after Vaxis reacquires terminal input.
func (b *Clipboard) Resume() {
	b.mu.Lock()
	if !b.stopped {
		b.ctx, b.cancel = context.WithCancel(context.Background())
	}
	b.mu.Unlock()
}

// Cancel permanently unblocks reads. It is safe to call repeatedly.
func (b *Clipboard) Cancel() {
	b.mu.Lock()
	if !b.stopped {
		b.stopped = true
		b.cancel()
	}
	b.mu.Unlock()
}
