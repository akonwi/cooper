package main

import (
	"charm.land/bubbles/v2/viewport"
	tea "charm.land/bubbletea/v2"
)

// The official pager's Update -> viewport.Update / View -> viewport.View shape,
// without tea.Program's terminal renderer, ticker, coalescing or I/O.
func prepare(lines []string) session {
	vp := viewport.New(viewport.WithWidth(80), viewport.WithHeight(24))
	vp.SoftWrap = false
	vp.SetContentLines(lines)
	output := vp.View()
	return session{
		step: func(direction int) {
			key := 'j'
			if direction < 0 {
				key = 'k'
			}
			if direction != 0 {
				var cmd tea.Cmd
				vp, cmd = vp.Update(tea.KeyPressMsg{Code: key, Text: string(key)})
				if cmd != nil {
					panic("unexpected asynchronous viewport command")
				}
			}
			output = vp.View()
		},
		view:  func() string { return output },
		close: func() {},
	}
}
