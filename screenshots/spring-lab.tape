# Requires VHS v0.11.0, ttyd, ffmpeg, gifsicle, and DejaVu Sans Mono.
# Install VHS: go install github.com/charmbracelet/vhs@v0.11.0
# From the repository root:
# (cd examples && ard build --out ../ard-out/spring_lab spring_lab.ard)
# vhs screenshots/spring-lab.tape
# gifsicle -O3 --colors 64 --batch screenshots/spring-lab.gif
Output screenshots/spring-lab.gif

Require ard-out/spring_lab
Set Shell "bash"
Set FontFamily "DejaVu Sans Mono"
Set FontSize 18
Set Width 960
Set Height 600
Set Padding 16
Set Theme "Catppuccin Mocha"
Set Framerate 15
Set TypingSpeed 30ms
Set CursorBlink false
Set WaitTimeout 15s

Hide
Type "./ard-out/spring_lab"
Enter
Wait+Screen /FAST/
Show

# Compare the first response, freeze it, then redirect existing momentum.
Sleep 400ms
Space
Sleep 800ms
Space
Sleep 600ms
Left
Sleep 600ms
Type "c"
Wait+Screen /(?s)BOUNCY.*SETTLED.*BALANCED.*SETTLED.*CRITICAL.*SETTLED.*HEAVY.*SETTLED.*SLOW.*SETTLED.*FAST.*SETTLED/
Sleep 800ms

Hide
Ctrl+C
