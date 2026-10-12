# 0027: Define Program Status Reporting

## Status

Accepted

## Context

The [Program Status Protocol (OSC 7501)](https://www.superlogical.com/rex/docs/build/program-status)
lets a program tell its terminal what it is doing: idle, working (with optional
progress), blocked on the user (`permission`, `question`, or `auth`), done, or
failed, with an optional title and message. Terminals and agent inboxes can then
stop guessing program state from window titles and screen contents. Kit wants to
report agent turns and pending requests this way. This decision targets spec
revision 0.4.

The protocol is richer than OSC 9;4 progress ([ADR 0010](./0010-define-terminal-progress-reporting.md)).
The terminal stores one *record* per id. Each report replaces its record
completely. Ids form a `/`-separated hierarchy, and clearing an id also removes
every record beneath it. A `clear` without an id removes every record, so the
root record cannot be cleared on its own. The terminal drops `working` and
`blocked` records when the process attached to the pty exits or a new shell
prompt begins (OSC 133). `done` and `error` records survive both events. The
terminal decides when the user has seen them.

Upstream Vaxis implements the program side
([rockorager/vaxis@32c9e22](https://github.com/rockorager/vaxis/commit/32c9e22)).
`SetProgramStatus` and `ClearProgramStatus` encode the body through Vaxis's
serialized control writer. They base64-encode text, delete control characters,
truncate at UTF-8 boundaries to the protocol limits, and validate ids and app
names. Vaxis also sends the feature query `OSC 7501 ; ?` with its startup
queries and reports the answer through `CanProgramStatus`.

## Decision

### Values

`cooper/program_status` defines Ard-native values. Ard enums cannot carry data,
so the state is a union of structs. Combinations the protocol ignores, such as
a kind without `blocked` or progress with `done`, cannot be written.

```ard
enum Kind { permission, question, auth }

struct Idle {}
struct Working { progress: Int? }
struct Blocked { kind: Kind?, progress: Int? }
struct Done {}
struct Failed {}

type State = Idle | Working | Blocked | Done | Failed

struct Report {
  state: State,
  app: Str?,
  title: Str?,
  message: Str?,
  id: Str?,
}

struct Clear { id: Str? }

type Update = Report | Clear
```

`Failed` maps to the protocol's `error` state. It avoids shadowing Ard's
built-in `Error` type. An absent `progress` means indeterminate, and an absent
`id` addresses the root record.

### Runtime API

```ard
impl runtime::Runtime {
  fn mut program_status(report: program_status::Report) Bool
  fn mut clear_program_status(id: Str) Bool
  fn mut clear_all_program_status() Bool
  fn mut program_status_supported() Bool
}
```

```ard
let _ = application.context.program_status(
  program_status::Report{state: program_status::Working{}, app: "kit"},
)
```

Each method returns whether the update was sent. Clearing is split because the
protocol cannot clear the root record alone: `clear_program_status(id)` removes
a record and its descendants, and `clear_all_program_status()` removes every
record. Reports and clears are accepted in the same lifecycle phases as
progress. They are rejected while suspended, stopping, or destroyed, and by
detached runtimes. They do not request a Cooper frame.

`program_status_supported()` reports whether the terminal answered the startup
feature query. Reports are **not** gated on it: the protocol lets programs
report without asking first, and a terminal that acts on reports may not
answer the query. Applications can use it to avoid double notifications when the
terminal notifies on record changes.

### Validation and text

Cooper validates in Ard before anything reaches Vaxis. Contract violations
panic, as with progress:

- `progress` outside 0–100;
- an `app` that is not 1–32 characters from `[A-Za-z0-9_.+-]`;
- an `id` that is empty, or is not at most 8 `/`-separated segments of 1–32
  such characters and 128 bytes in total. An empty id panics; omit `id` to
  address the root record.

The protocol tells terminals to discard any report whose text contains a
control character. Cooper therefore replaces every control character in
`title` and `message` with a space, as it does for terminal titles. Vaxis would
delete them instead. Vaxis truncates the text to the protocol limits (`title`
192 bytes, `msg` 2048 bytes). Empty text is treated as absent, because Vaxis
omits it and each report replaces its record completely.
Validation fails before Vaxis is called, so an error returned by Vaxis indicates
a Cooper bug.

### Records and lifecycle

The runtime keeps the last report it sent for each id, ordered from least to
most recently updated. Clearing an id also forgets the records beneath it. Like
the terminal, Cooper keeps at most 256 records and forgets the least recently
updated one first. Records describe the running
program only while they are `idle`, `working`, or `blocked` (*live*). A `done`
or `failed` report belongs to the terminal once sent: the terminal decides when
the user has seen it.

- **Repeats.** Every accepted report is sent, including one identical to the
  current record, as progress reports are. A repeat recreates a record the
  terminal lost through a full reset (RIS) or its own eviction, and refreshes
  the record's recency. A repeated completion is a new event. Applications
  should report on state changes rather than on every frame or streamed token.
- **Suspend.** Each `working` or `blocked` record is reported as `idle`, keeping
  its `app`, `title`, and `id`. The program is no longer running, and reporting
  `idle` avoids clearing the root record, which would remove every record.
  The original reports are kept.
- **Resume, and failed suspension.** The live records are sent again. `done`
  and `failed` records are never repeated, because the user may already have
  dismissed them.
- **Destruction.** If Cooper reported the root record and holds no `done` or
  `failed` record, it sends a single `clear` without an id. Otherwise it never
  sends one, because it would also remove records other programs left on the
  terminal, including their unseen completions. Instead it clears each live
  record by id, unless a `done` or `failed` record lies beneath it. Such a
  record, including a live root record, is reported as `idle` instead and stays
  in place. Records beneath an already-cleared record are not cleared again.
  With no records, nothing is sent. Cooper does not rely on the terminal
  dropping records at process exit: the pty's process is usually the shell, so
  without OSC 133 shell integration the terminal never sees the application
  exit.
- **Destruction while suspended.** In alt-screen mode, Cooper resumes the
  terminal for cleanup and then applies the destruction rules. In the primary-screen
  modes, or if resuming fails, nothing more is sent. The `idle` reports sent at
  suspension stay on the terminal, which the protocol allows it to drop.
  Headless tests follow the alt-screen behavior.

The runtime lifecycle lock orders calls against suspension, resume, and
destruction, as it does for progress. Vaxis's control writer serializes the
output with rendered frames.

### Backend support

Reports are sent by default. OSC 7501 has a number of its own, unlike the OSC 9
number that progress shares with iTerm2 notifications, and terminals must ignore
OSCs they do not recognize. Inside tmux, GNU Screen, and Zellij, reports are
disabled, because a multiplexer would swallow them. `COOPER_PROGRAM_STATUS=0|false|off`
disables them, and a multiplexer still wins over a forced enable.

### Testing

`testing::new` accepts `program_status_unsupported: true` to simulate a terminal
that cannot receive reports, and `program_status_detected: true` to simulate one
that answered the feature query. `TestApp.program_status_updates()` returns the
ordered logical updates sent, including those sent by suspension, resume, and
destruction. It remains readable after destruction.

Headless tests cover every state and field, repeated reports, text
cleaning, contract panics, suspend and resume, every destruction case,
subtree clearing, unsupported and detached runtimes, detection, and environment
policy. PTY coverage in `examples/test_notification.py` verifies the OSC 7501
bytes, idle-then-restore across suspension, teardown that leaves a `done` record
in place, and the disabled environment.

## Consequences

Applications report program state without encoding the protocol, and the spec's
lifetime rules are applied by Cooper rather than every application. A terminal
cannot be left showing a stale `working` or `blocked` record after normal
suspension or teardown. `done` records the user has not seen survive teardown
and are never resurrected.

Following future spec revisions is contained. New keys are safe, because
terminals ignore unknown keys. A new state needs feature detection, because an
older terminal ignores a report with a state it does not recognize.

## Related

- [ADR 0002: Define the Application API](./0002-define-application-api.md)
- [ADR 0009: Define Terminal-Mediated Notifications](./0009-define-terminal-mediated-notifications.md)
- [ADR 0010: Define Terminal Progress Reporting](./0010-define-terminal-progress-reporting.md)
- [ADR 0012: Define Terminal Title Updates](./0012-define-terminal-title-updates.md)
- [ADR 0013: Consolidate Context into Runtime](./0013-consolidate-context-into-runtime.md)
- [Program Status Protocol (OSC 7501)](https://www.superlogical.com/rex/docs/build/program-status)
- [Issue #17](https://github.com/akonwi/cooper/issues/17)
