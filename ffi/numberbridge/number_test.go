package numberbridge

import (
	"strconv"
	"testing"
)

func TestIntFromInt64(t *testing.T) {
	for _, value := range []int64{0, 42, -42, 1<<31 - 1, -1 << 31} {
		got, err := IntFromInt64(value)
		if err != nil || int64(got) != value {
			t.Fatalf("IntFromInt64(%d) = %d, %v", value, got, err)
		}
	}
	for _, value := range []int64{1 << 31, -1<<31 - 1, 1<<63 - 1, -1 << 63} {
		got, err := IntFromInt64(value)
		if strconv.IntSize == 32 {
			if err == nil {
				t.Fatalf("IntFromInt64(%d) accepted overflow", value)
			}
		} else if err != nil || int64(got) != value {
			t.Fatalf("IntFromInt64(%d) = %d, %v", value, got, err)
		}
	}
}
