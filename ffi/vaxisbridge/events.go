package vaxisbridge

import vaxis "github.com/akonwi/vaxis"

// HasModifier is the only event conversion retained in Go because Ard does
// not expose bitwise operators.
func HasModifier(modifiers, flag vaxis.ModifierMask) bool {
	return modifiers&flag != 0
}
