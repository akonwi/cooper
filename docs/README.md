# vaxis-ard docs

Design notes and investigations for the Ard-native retained-mode framework.
The previous `vaxis/ui` binding notes remain as historical references while the
new implementation is developed.

## Architecture

- [architecture.md](./architecture.md) — accepted retained-widget architecture,
  layout and surface model, event-routing direction, runtime responsibilities,
  verification strategy, and implementation milestones.

## Historical binding notes

- [events-and-focus.md](./events-and-focus.md) — upstream `vaxis/ui` event
  dispatch, shortcuts, actions, focus widgets, and routing pitfalls.
- [widget-reconciliation.md](./widget-reconciliation.md) — upstream `vaxis/ui`
  reconciliation behavior and the type-change repaint pitfall.

These historical notes describe the implementation being replaced. They are
useful prior art, but they do not define behavior for the retained framework.

## Conventions

- State the decision or behavior being documented.
- Link the relevant upstream Vaxis source or Ard language change.
- Add focused headless or PTY coverage when a document records executable
  behavior.
