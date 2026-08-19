# vaxis-ard examples

Example TUI programs for the retained framework and historical bindings.

Each example is a single `.ard` file with its own `fn main()` and shares the
same `ard.toml` and `go.mod`.

```
retained_input.ard – retained state, surface rendering, editing, and cursor
counter.ard        – legacy increment/decrement counter
todo.ard           – legacy todo list with inline editing
tic_tac_toe.ard    – legacy tic-tac-toe game
demo.ard           – legacy vaxis/ui widget showcase
```

## Build

```sh
ard build retained_input.ard # → ./retained_input
ard build counter.ard        # → ./counter
ard build todo.ard          # → ./todo
ard build tic_tac_toe.ard   # → ./tic_tac_toe
ard build demo.ard          # → ./demo
```

## Run

```sh
ard run retained_input.ard
ard run counter.ard
ard run todo.ard
ard run tic_tac_toe.ard
ard run demo.ard
```

## Test

Each example has a Python PTY smoke test that builds the binary, spawns it
under a pseudoterminal, feeds keystrokes, and asserts on visible output:

```sh
python3 test_retained_input.py
python3 test_counter.py
python3 test_todo.py
python3 test_tic_tac_toe.py
python3 test_demo.py
```

## Controls

### retained_input

- type to insert text
- arrows / Home / End: move the cursor
- Backspace / Delete: remove a grapheme
- `Ctrl+C`: quit

### counter
- `up` / `right` / `k` / `l` / `+`: increment
- `down` / `left` / `j` / `h` / `-`: decrement
- `r`: reset
- `q` or `Ctrl+C`: quit

### todo
- `up` / `down` or `k` / `j`: move selection
- `enter`: toggle selected item
- `e`: edit selected item
- `a`: add a new empty todo and start editing it
- `d`: delete selected item
- while editing: type to insert, `backspace` to delete, `enter` to save, `q` to cancel
- `r`: reset sample todos
- `q` or `Ctrl+C`: quit

### tic-tac-toe
- arrows or `h` / `j` / `k` / `l`: move selection
- `1`–`9`: jump to a square
- `enter` / `space`: play selected square
- `r`: restart
- `q` or `Ctrl+C`: quit

### demo
- `n` / `p`: next / previous page
- `Tab`: move focus
- `Alt+K`: command palette
- `Alt+P`: profile overlay
- `q`: quit
