# Native Go Bubble Tea pager reference

Original benchmark adapter using the official
[Bubble Tea pager](https://github.com/charmbracelet/bubbletea/blob/v2.0.9/examples/pager/main.go)
pattern: delegate messages to `viewport.Update`, then call `viewport.View`.
Dependencies are pinned to Bubble Tea v2.0.9 and Bubbles v2.2.1 in this isolated
Go module. Both upstream projects are MIT licensed; no example source or assets
are vendored. `main.go` is also the shared instrumentation/data/oracle driver for
both Cooper binaries. `cooper.go.template` replaces only the adapter when the
runner builds those binaries.

```sh
# Native-only smoke; prints timing samples and a representative frame as JSON.
go run .

# From the Cooper repository root:
git fetch origin
git worktree add --detach /tmp/cooper-bubbletea-main origin/main
python3 benchmarks/compare_bubbletea.py /tmp/cooper-bubbletea-main . \
  --samples 30 --output /tmp/bubbletea-pager-results.json
git worktree remove /tmp/cooper-bubbletea-main
```

Run without competing tests/builds. The comparator copies only the Ard fixture
into the baseline, refusing to overwrite different content, and removes its
copy afterward. It restores generated Go entry files after instrumented builds.
Cooper's production modules do not acquire Bubble Tea dependencies.

The program does not start `tea.Program`, use `WithoutRenderer`, impose a frame
rate, or write to a terminal. Every event explicitly generates a view; unchanged
steps generate one too. There is no ANSI/color, wrapping, searching or selection.
This is **pager update/view generation**, not terminal rendering or a general
framework score. See [results and limitations](../../docs/bubbletea-pager-benchmark.md).
