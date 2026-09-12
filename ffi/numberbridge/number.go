package numberbridge

// Widen exposes Float32-to-Float64 conversion, which Ard v0.41 does not
// currently provide. Numeric behavior remains implemented in Ard.
func Widen(value float32) float64 { return float64(value) }
