package clock

import "testing"

func TestIntFromInt64(t *testing.T) {
	got, err := IntFromInt64(42)
	if err != nil || got != 42 {
		t.Fatalf("IntFromInt64(42) = %d, %v", got, err)
	}
}

func TestMillisecondsNeverMovesBackward(t *testing.T) {
	before := Milliseconds()
	after := Milliseconds()
	if after < before {
		t.Fatalf("monotonic clock moved backward: before=%d after=%d", before, after)
	}
}
