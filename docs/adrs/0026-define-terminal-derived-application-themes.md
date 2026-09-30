# ADR 0026: Define terminal-derived application themes

## Status

Accepted

## Context

Terminal applications need readable semantic colors that follow the host's
foreground, background, and ANSI palette. Applications otherwise duplicate OSC
4/10/11 discovery, light/dark detection, contrast-aware palette generation, and
theme-change handling. A raw color report alone is not an application theme and
would conflict with ADR 0008's reservation of `theme::Theme` for semantic roles.

Vaxis already discovers OSC color-report capabilities with DA1 as its startup
sentinel, exposes cancellable queries, and enables color-scheme notifications
through mode 2031 and DSR 996/997.

## Decision

Cooper owns an Ard-native `theme::Theme` with resolved semantic roles:
background and foreground, surfaces, primary and accent states, status colors,
muted and disabled foregrounds, selection, and border. `Theme.terminal_colors`
preserves the optional RGB facts reported by the host. Missing reports use
Cooper defaults; they never make semantic roles optional.

Every live App owns a theme query service. `application.theme()` is available
immediately after `app()` and therefore supports initial UI construction before
`start()` or `run()`. Before startup it performs the bounded query on the calling
fiber. Once the App is active it returns the cached current theme without
blocking, so it is safe in application callbacks. Headless and unavailable
runtimes return the default resolved theme.

`application.on_theme_changed(handler)` publishes deduplicated complete themes.
Cooper refreshes asynchronously after Vaxis `ColorThemeUpdate` events and after
terminal focus is gained as a compatibility fallback. CUI Context exposes the
current theme and a mount-scoped change subscription.

Queries use one 200 ms batch deadline. Suspension and destruction cancel active
queries. Concurrent calls serialize rather than issuing overlapping terminal
requests; automatic refresh triggers coalesce while one refresh is active.

## Consequences

Applications can construct an App, query its theme before mounting the initial
UI, and remove private `/dev/tty` query shims and palette-generation ports while
retaining their own semantic overrides. User theme definitions are reapplied
over each new Cooper system theme.

The general `theme` namespace is no longer merely reserved: it now begins the
Context-owned semantic theme system anticipated by ADR 0008. Built-in controls
may adopt these roles incrementally; local `Appearance` remains a per-control
patch rather than a competing theme.

Cooper intentionally provides no independent terminal query. Color discovery
always uses the Vaxis session owned by an App, preserving one terminal owner.

## Related

- [ADR 0002](./0002-define-application-api.md)
- [ADR 0008](./0008-define-select-controls-and-appearance-overrides.md)
- [ADR 0013](./0013-consolidate-context-into-runtime.md)
