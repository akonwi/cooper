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

## PTY smoke test

The smoke test builds the example, starts it under a pseudoterminal, edits text,
resizes the terminal, and verifies a clean exit:

```sh
python3 test_input.py
```

Set `ARD` to select a compiler executable when needed.
