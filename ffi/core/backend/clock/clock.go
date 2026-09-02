package clock

import (
	"fmt"
	"time"
)

var started = time.Now()

// Milliseconds returns monotonic milliseconds elapsed since package initialization.
func Milliseconds() int64 {
	return time.Since(started).Milliseconds()
}

// SleepMilliseconds blocks for at least the requested non-negative duration.
func SleepMilliseconds(milliseconds int64) {
	if milliseconds > 0 {
		time.Sleep(time.Duration(milliseconds) * time.Millisecond)
	}
}

// IntFromInt64 converts a sized clock value to the platform Int boundary.
func IntFromInt64(value int64) (int, error) {
	converted := int(value)
	if int64(converted) != value {
		return 0, fmt.Errorf("%d exceeds the platform Int range", value)
	}
	return converted, nil
}
