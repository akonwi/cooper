# Cooper docs

Design decisions for Cooper's Ard-native retained-mode framework.

## Canonical design

- [ADR 0002](./adrs/0002-define-application-api.md) — accepted imperative
  application API, runtime model, OpenTUI lineage, and intentionally deferred
  extension surfaces.
- [ADR 0003](./adrs/0003-define-interaction-focus-and-selection.md) — accepted
  pointer, focus, terminal-focus, and selection semantics.
- [ADR 0004](./adrs/0004-define-input-editor-and-keybindings.md) — accepted
  Ard-native editor state, actions, and default CLI keybindings.
- [ADR 0005](./adrs/0005-define-rich-text-wrapping-and-multi-click-selection.md) — accepted
  rich Text spans, Unicode wrapping, overflow, links, and double-click selection.
- [ADR 0006](./adrs/0006-define-terminal-clipboard-access.md) — accepted OSC 52
  clipboard reads, writes, clears, and App-lifetime semantics.
- [ADR 0007](./adrs/0007-define-scrollbars-and-two-axis-scrolling.md) — accepted
  standalone Scrollbars, built-in ScrollBox gutters, and sequenced two-axis scrolling.
- [ADR 0008](./adrs/0008-define-select-controls-and-appearance-overrides.md) — accepted
  compact Select menus, TabSelect, committed choice state, and local Appearance patches.
- [ADR 0009](./adrs/0009-define-terminal-mediated-notifications.md) — accepted
  Context notification requests, conservative protocol selection, and lifecycle semantics.
- [ADR 0010](./adrs/0010-define-terminal-progress-reporting.md) — accepted
  Context terminal progress states, Ghostty OSC 9;4 output, and lifecycle cleanup.

## Architecture Decision Records

Significant architecture decisions are recorded in [`adrs/`](./adrs/).

| ADR | Status | Decision |
| --- | --- | --- |
| [0001](./adrs/0001-record-architecture-decisions.md) | Accepted | Record architecture decisions |
| [0002](./adrs/0002-define-application-api.md) | Accepted | Define the application API |
| [0003](./adrs/0003-define-interaction-focus-and-selection.md) | Accepted | Define interaction, focus, and selection |
| [0004](./adrs/0004-define-input-editor-and-keybindings.md) | Accepted | Define Input editor state and CLI keybindings |
| [0005](./adrs/0005-define-rich-text-wrapping-and-multi-click-selection.md) | Accepted | Define rich Text, wrapping, and multi-click selection |
| [0006](./adrs/0006-define-terminal-clipboard-access.md) | Accepted | Define terminal clipboard access |
| [0007](./adrs/0007-define-scrollbars-and-two-axis-scrolling.md) | Accepted | Define Scrollbars and two-axis scrolling |
| [0008](./adrs/0008-define-select-controls-and-appearance-overrides.md) | Accepted | Define Select, TabSelect, and Appearance overrides |
| [0009](./adrs/0009-define-terminal-mediated-notifications.md) | Accepted | Define terminal-mediated notifications |
| [0010](./adrs/0010-define-terminal-progress-reporting.md) | Accepted | Define terminal progress reporting |

### Add an ADR

1. Choose the next four-digit sequence number.
2. Create `docs/adrs/NNNN-short-title.md`.
3. Use the headings `Status`, `Context`, `Decision`, `Consequences`, and
   `Related`.
4. Start unresolved decisions as `Proposed` and update their status when
   resolved.
5. Add the ADR to the table above.

Accepted ADRs preserve the rationale at the time of the decision. Replace an
accepted decision with a new ADR whose `Related` section links to the ADR it
supersedes.

## Conventions

- State the decision or behavior being documented.
- Link relevant upstream Vaxis source or Ard language changes.
- Add focused headless or PTY coverage when a document records executable
  behavior.
