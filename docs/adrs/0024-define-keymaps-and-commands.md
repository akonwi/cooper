# 0024: Define Keymaps and Commands

## Status

Accepted and implemented.

## Decision

Cooper owns an Ard-native keymap service within each Runtime. `Key` describes a
canonical name and exact modifiers; `KeyEvent` remains the delivered occurrence.
Bindings explicitly select press, press-and-repeat, or release. Application
commands default to press only; control maps retain press-and-repeat defaults.

Commands separate operations from keys. `TypedCommand<$Args>` offers `invoke`,
`with`, and `with_lazy`. `SimpleCommand` offers `invoke()` and `with()`.
Both implement the non-generic `Command` metadata trait and produce the same
non-generic `Invocation`. `enabled: fn() Bool` defaults to true and is checked
before evaluating lazy arguments. Discovery never evaluates argument providers.
Handlers return whether they handled an invocation, not whether state changed.
No dynamic argument casts or general intent/ancestor action lookup are needed.

Application, exact-focus, and focus-within scopes are explicit. Eligible layers
sort by descending priority, then specificity, then newest registration. Within
a layer bindings use declaration order. Existing Runtime listeners, live Ctrl+C
policy, focused listeners and CUI bubbling precede keymaps; control defaults
follow them. Prevention suppresses keymaps and defaults. Stopping propagation
skips keymaps but still permits an already-reached control's default. No focus
fallback or Tab traversal is introduced. Ctrl+C commands require opting out of
the existing automatic exit policy.

Registration and cleanup are Runtime-owned, UI-thread-only, and idempotent.
CUI owns declarative registrations and preserves precedence through updates.
Dispatch snapshots candidates, skips removed registrations, and does not use
invalidated focus routes. Hidden/detached focus scopes are inactive.

Controls expose typed actions, `perform`, default maps, and replacement maps.
Actions keep existing validation, callbacks, selection and rendering semantics.
Removing a mapping permits fallback; consuming a key suppresses it. Empty maps
disable mapped actions without disabling ordinary text insertion. Binding one
key replaces that key/trigger, not every alias for an action.

Discovery exposes command metadata, registered/eligible bindings and shadowing.
Labels come from the effective map; arbitrary raw listeners and handlers that
decline cannot be predicted. Screen modes do not create keyboard scopes.

Sequences, parser plugins, physical-layout matching, persistence, help widgets,
and general routed intents are deferred. OpenTUI informs binding configuration
and discovery; Vaxis UI informs the separation of operations from input.

## Language feasibility

Ard 0.42.0 compiler probes verified generic structs implementing a non-generic
trait, heterogeneous `[Command]` catalogs, cross-module typed invocation,
closure-bound `Invocation` lists, and both command forms. Incorrect argument
types are rejected statically. Mutable models are required when lazy providers
must observe changing state rather than a captured scalar snapshot.

## Verification

Use deterministic tests for matching, invocation, availability, scope ordering,
mutation during dispatch, focus changes, control no-ops, maps, discovery and CUI
reconciliation/cleanup. Preserve existing control/event suites and cover live
Ctrl+C and terminal input through PTY tests.
