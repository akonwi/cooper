module cooper_examples

go 1.27.0

replace github.com/akonwi/cooper => ..

// Ard source imports Cooper and Vaxis directly through the Go backend.
require (
	github.com/akonwi/cooper v0.0.0
	github.com/akonwi/vaxis v0.0.0-20260913113926-34e520204135
)

require (
	github.com/rockorager/go-uucode v1.2.2 // indirect
	golang.org/x/image v0.46.0 // indirect
	golang.org/x/sys v0.48.0 // indirect
	golang.org/x/term v0.10.0 // indirect
)
