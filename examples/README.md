# Cooper examples

## Input

`input.ard` exercises Cooper's first retained widget and direct Vaxis runtime.

```sh
ard build input.ard --out input
./input
```

Controls:

- type or paste to insert text;
- Left/Right/Home/End move the cursor;
- Backspace/Delete remove one grapheme;
- Ctrl+C exits.

## Filesystem explorer

`explorer.ard` is a responsive Miller-column browser rooted at the current
working directory.

```sh
ard run explorer.ard
```

Controls:

- Up/Down select entries;
- Right/Enter opens a selected directory;
- Left, Backspace, or `../` navigates upward;
- `/` focuses search and Escape returns to the directory;
- click selects and opens directories;
- the mouse wheel scrolls a pane;
- Ctrl+C exits.

## PTY smoke tests

The smoke tests build examples, start them under a pseudoterminal, exercise
interaction, and verify a clean exit:

```sh
python3 test_input.py
python3 test_explorer.py
```

Set `ARD` to select a compiler executable when needed.
