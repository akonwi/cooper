package numberbridge

import (
	"fmt"
	"math"
)

// Widen exposes the numeric conversion missing from Ard's Float32 API.
// Layout arithmetic and rounding policy remain in Ard.
func Widen(value float32) float64 { return float64(value) }

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
