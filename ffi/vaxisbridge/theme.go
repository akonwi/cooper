package vaxisbridge

import (
	"context"

	vaxis "github.com/akonwi/vaxis"
)

// RGB is an optional resolved terminal color. Valid distinguishes an
// unanswered query from black.
type RGB struct {
	Red   uint8
	Green uint8
	Blue  uint8
	Valid bool
}

// TerminalColors contains OSC 10, OSC 11, and ANSI palette 0-7 replies.
type TerminalColors struct {
	Foreground RGB
	Background RGB
	Palette    []RGB
}

func resolved(color vaxis.Color) RGB {
	params := color.Params()
	if len(params) != 3 {
		return RGB{}
	}
	return RGB{Red: params[0], Green: params[1], Blue: params[2], Valid: true}
}

// QueryTerminalColors uses Vaxis's active parser and capability detection.
// The caller owns cancellation and must not block Vaxis's event-loop goroutine.
func QueryTerminalColors(ctx context.Context, terminal *vaxis.Vaxis) TerminalColors {
	result := TerminalColors{Palette: make([]RGB, 8)}
	result.Foreground = resolved(terminal.QueryForegroundContext(ctx))
	result.Background = resolved(terminal.QueryBackgroundContext(ctx))
	for index := range result.Palette {
		result.Palette[index] = resolved(terminal.QueryColorContext(ctx, vaxis.IndexColor(uint8(index))))
	}
	return result
}
