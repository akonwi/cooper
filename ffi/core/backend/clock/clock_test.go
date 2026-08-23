package clock

import "testing"

func TestMillisecondsNeverMovesBackward(t *testing.T) {
	before := Milliseconds()
	after := Milliseconds()
	if after < before {
		t.Fatalf("monotonic clock moved backward: before=%d after=%d", before, after)
	}
}
