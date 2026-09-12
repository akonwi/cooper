// Package contextbridge adapts Go return shapes that Ard cannot import.
package contextbridge

import "context"

// Cancellation packages context.WithCancel's two non-error results.
type Cancellation struct {
	Context context.Context
	Cancel  func()
}

func WithCancel(parent context.Context) Cancellation {
	ctx, cancel := context.WithCancel(parent)
	return Cancellation{Context: ctx, Cancel: cancel}
}
