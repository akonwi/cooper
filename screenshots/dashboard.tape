# Requires VHS v0.11.0, ttyd, ffmpeg, and DejaVu Sans Mono.
# Install VHS: go install github.com/charmbracelet/vhs@v0.11.0
# VHS v0.12.0 returned success without producing a GIF in this environment.
# Run from the repository root after building the example:
# (cd examples && ard build --out ../ard-out/dashboard dashboard.ard)
# vhs screenshots/dashboard.tape
Output screenshots/dashboard.gif

Require ard-out/dashboard
Set Shell "bash"
Set FontFamily "DejaVu Sans Mono"
Set FontSize 18
Set Width 1120
Set Height 640
Set Padding 16
Set Theme "Catppuccin Mocha"
Set Framerate 15
Set TypingSpeed 100ms
Set CursorBlink false

Hide
Type "./ard-out/dashboard"
Enter
Wait+Screen /State: RUNNING/
Sleep 1s
Show

# Watch live telemetry, then pause to inspect and insert an event.
Sleep 4s
Space
Sleep 1s
Type "a"
Sleep 2s

# Browse retained history and restore follow mode before resuming.
Up 3
Sleep 2s
Type "f"
Sleep 1s
Space
Sleep 4s

Hide
Type "q"
