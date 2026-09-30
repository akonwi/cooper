// Package contextbridge adapts Go return shapes that Ard cannot import.
package contextbridge

import (
	"context"
	"time"
)

// Cancellation packages context.WithCancel's two non-error results.
type Cancellation struct {
	Context context.Context
	Cancel  func()
}

func WithCancel(parent context.Context) Cancellation {
	ctx, cancel := context.WithCancel(parent)
	return Cancellation{Context: ctx, Cancel: cancel}
}

func WithTimeout(parent context.Context, milliseconds int64) Cancellation {
	ctx, cancel := context.WithTimeout(parent, time.Duration(milliseconds)*time.Millisecond)
	return Cancellation{Context: ctx, Cancel: cancel}
}
