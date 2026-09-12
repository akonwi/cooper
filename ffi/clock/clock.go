package clock

import "fmt"

// IntFromInt64 provides checked narrowing to platform Int. Ard v0.41.0
// supports sized scalar constructors but does not expose Int::from.
func IntFromInt64(value int64) (int, error) {
	converted := int(value)
	if int64(converted) != value {
		return 0, fmt.Errorf("%d exceeds the platform Int range", value)
	}
	return converted, nil
}
