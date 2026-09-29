# Cooper docs

Design decisions and implementation history for Cooper's retained-mode framework.

## Architecture Decision Records

Canonical design decisions live in [`adrs/`](./adrs/). Each ADR records the
context, decision, and consequences of a significant architectural choice.
Accepted ADRs preserve the rationale at the time of the decision; replace an
accepted decision with a new ADR whose `Related` section links to the ADR it
supersedes.

### Add an ADR

1. Choose the next four-digit sequence number.
2. Create `docs/adrs/NNNN-short-title.md`.
3. Use the headings `Status`, `Context`, `Decision`, `Consequences`, and
   `Related`.
4. Start unresolved decisions as `Proposed` and update their status when
   resolved.

## Framework guides

- [Declarative components](./declarative.md) — `cooper/cui` framework guide.
- [Keymaps and commands](./keymaps.md) — typed commands, scoped bindings, and
  shortcut discovery.

## Benchmarks and implementation history

- [Benchmark guide](../benchmarks/README.md) — runners, reproduction, and
  output storage.
- [Performance checkpoints](./performance-optimization.md) — optimization
  findings and live-heap measurements.

Historical reports describe their named revisions, not current main. Keep their
findings and design rationale here; generated benchmark data belongs outside Git.

## Conventions

- State the decision or behavior being documented.
- Link relevant upstream Vaxis source or Ard language changes.
- Add focused headless or PTY coverage when a document records executable
  behavior.
