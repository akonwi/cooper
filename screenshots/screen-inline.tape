# Build: (cd examples && ard build --out ../ard-out/screen_modes screen_modes.ard)
# Record: VHS_NO_SANDBOX=1 vhs screenshots/screen-inline.tape
# Requires VHS v0.11.0, ttyd, ffmpeg, and DejaVu Sans Mono.
Output .amp/in/artifacts/screen-inline.gif
Require ard-out/screen_modes
Set Shell "bash"
Set FontFamily "DejaVu Sans Mono"
Set FontSize 18
Set Width 1000
Set Height 360
Set Padding 16
Set Theme "Catppuccin Mocha"
Set Framerate 12
Set TypingSpeed 25ms
Set CursorBlink false
Set WaitTimeout 15s
Hide
Type "export PS1='$ '; clear; printf 'Previous shell output\nBuild: compiled 12 modules\nTests: all passed\n'"
Enter
Sleep 500ms
Show
Sleep 1s
Type "COOPER_SCREEN_MODE=inline ./ard-out/screen_modes"
Enter
Wait+Screen /SCREEN READY/
Sleep 1s
Type " - typing"
Sleep 1s
Ctrl+O
Sleep 600ms
Ctrl+O
Sleep 600ms
Ctrl+O
Sleep 600ms
Ctrl+O
Sleep 600ms
Ctrl+O
Sleep 600ms
Ctrl+O
Sleep 600ms
Ctrl+O
Sleep 600ms
Ctrl+O
Sleep 600ms
Ctrl+O
Sleep 600ms
Ctrl+O
Wait+Screen /OUTPUT 10/
Sleep 2s
Escape
# VHS v0.11's Screen wait misses new lines after scrollback grows.
# Keep the visible exit in the recording and inspect the final frame.
Sleep 3s
