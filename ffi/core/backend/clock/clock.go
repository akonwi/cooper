package clock

import "time"

var started = time.Now()

// Milliseconds returns monotonic milliseconds elapsed since package initialization.
func Milliseconds() int64 {
	return time.Since(started).Milliseconds()
}
