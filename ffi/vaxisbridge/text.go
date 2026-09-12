package vaxisbridge

import "unicode/utf8"

// ValidHyperlink rejects terminal controls and malformed UTF-8 before a value
// can reach Vaxis's OSC 8 fields.
func ValidHyperlink(value string) bool {
	if !utf8.ValidString(value) {
		return false
	}
	for _, r := range value {
		if r <= 0x1f || (r >= 0x7f && r <= 0x9f) {
			return false
		}
	}
	return true
}
