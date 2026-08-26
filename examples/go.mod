module cooper_examples

go 1.27.0

replace github.com/akonwi/cooper => ..

// Ard source imports Cooper and Vaxis directly through the Go backend.
require (
	github.com/akonwi/cooper v0.0.0
	go.rockorager.dev/vaxis v0.17.2-0.20260811162040-8a93a9a0e2e7
)

require (
	github.com/AnatoleLucet/tess v1.0.0-rc.2.0.20260327154250-57529f93db9d // indirect
	github.com/rockorager/go-uucode v1.2.0 // indirect
	golang.org/x/sys v0.10.0 // indirect
	golang.org/x/term v0.10.0 // indirect
)
