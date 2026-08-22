# 0001: Record Architecture Decisions

## Status

Accepted

## Context

Architectural decisions benefit from a durable record of their context,
tradeoffs, and consequences. Keeping those records in the repository makes them
reviewable alongside the code and available to future contributors.

## Decision

Record significant architecture decisions as Architecture Decision Records in
`docs/adrs/`.

ADRs use four-digit sequential numbers and kebab-case filenames:

```text
NNNN-short-title.md
```

Each ADR contains these sections:

- Status
- Context
- Decision
- Consequences
- Related

New ADRs begin as `Proposed` and become `Accepted`, `Rejected`, or `Superseded`
when resolved. An accepted decision is changed by writing a new ADR that links
to and supersedes it rather than rewriting its history.

## Consequences

- Significant decisions have a consistent, discoverable history.
- Contributors must decide when a change warrants an ADR and maintain the ADR
  index.
- Superseding decisions create additional records instead of silently replacing
  prior rationale.

## Related

None.
