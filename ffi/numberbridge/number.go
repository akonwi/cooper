package numberbridge

import "fmt"

// Widen exposes Float32-to-Float64 conversion, which Ard v0.41 does not
// currently provide. Numeric behavior remains implemented in Ard.
func Widen(value float32) float64 { return float64(value) }

// IntFromInt64 provides checked narrowing to platform Int. Ard v0.41.0
// supports sized scalar constructors but does not expose Int::from.
func IntFromInt64(value int64) (int, error) {
	converted := int(value)
	if int64(converted) != value {
		return 0, fmt.Errorf("%d exceeds the platform Int range", value)
	}
	return converted, nil
}
