package numberbridge

import (
	"fmt"
	"math"
)

// RoundedInt rounds value to the nearest integer, with halves away from zero,
// and rejects values outside the platform int range.
func RoundedInt(value float64) (int, error) {
	if math.IsNaN(value) || math.IsInf(value, 0) {
		return 0, fmt.Errorf("%v is not finite", value)
	}
	rounded := math.Round(value)
	limit := math.Ldexp(1, 31)
	if ^uint(0)>>63 == 1 {
		limit = math.Ldexp(1, 63)
	}
	if rounded >= limit || rounded < -limit {
		return 0, fmt.Errorf("%v exceeds the platform Int range", rounded)
	}
	return int(rounded), nil
}
