package numberbridge

import (
	"math"
	"testing"
)

func TestRoundedInt(t *testing.T) {
	for _, test := range []struct {
		value float64
		want  int
	}{
		{value: 4.5, want: 5},
		{value: -4.5, want: -5},
		{value: 4.4, want: 4},
	} {
		got, err := RoundedInt(test.value)
		if err != nil || got != test.want {
			t.Fatalf("RoundedInt(%v) = %d, %v; want %d", test.value, got, err, test.want)
		}
	}
}

func TestRoundedIntRejectsInvalidAndOutOfRangeValues(t *testing.T) {
	values := []float64{math.NaN(), math.Inf(1), math.Inf(-1)}
	if ^uint(0)>>63 == 1 {
		values = append(values, math.Pow(2, 63))
	} else {
		values = append(values, math.Pow(2, 31))
	}
	for _, value := range values {
		if _, err := RoundedInt(value); err == nil {
			t.Fatalf("RoundedInt(%v) did not reject invalid value", value)
		}
	}
}
