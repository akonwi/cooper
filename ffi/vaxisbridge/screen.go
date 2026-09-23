package vaxisbridge

import vaxis "github.com/akonwi/vaxis"

// PrimaryPosition adapts a three-result Go method, which Ard cannot import.
type PrimaryPosition struct {
	Row        int
	Generation uint64
	Valid      bool
}

func ScreenPosition(terminal *vaxis.Vaxis) PrimaryPosition {
	row, generation, valid := terminal.PrimaryScreenOrigin()
	return PrimaryPosition{Row: row, Generation: generation, Valid: valid}
}
