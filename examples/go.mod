module cooper_examples

go 1.26

replace go.rockorager.dev/vaxis => ../../vaxis

replace cooper => ..

require (
	cooper v0.0.0
	go.rockorager.dev/vaxis v0.16.0
)

require (
	github.com/AnatoleLucet/tess v1.0.0-rc.2 // indirect
	github.com/rockorager/go-uucode v1.2.0 // indirect
	golang.org/x/sys v0.10.0 // indirect
	golang.org/x/term v0.10.0 // indirect
)
