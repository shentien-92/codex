# fix local codex /new crash

## Goal

Fix the local Codex TUI crash/exit that happens when the user runs `/new`.

## What I already know

* User report: opening local Codex and entering `/new` causes an error and exits.
* `/new` maps to `SlashCommand::New` in `codex-rs/tui/src/slash_command.rs`.
* `SlashCommand::New` dispatches `AppEvent::NewSession` in `codex-rs/tui/src/chatwidget/slash_dispatch.rs`.
* `AppEvent::NewSession` calls `start_fresh_session_with_summary_hint(...)` in `codex-rs/tui/src/app/event_dispatch.rs`.
* TUI code style is governed by the project AGENTS.md and `codex-rs/tui/styles.md`.

## Assumptions

* `/new` should start a fresh TUI chat without exiting the process.
* If starting the fresh session fails, the TUI should surface an error in the chat history and continue running instead of crashing.
* The fix should be narrow and avoid broader session lifecycle refactors.

## Requirements

* Reproduce the `/new` failure locally or in a focused test.
* Identify the failing code path.
* Fix the failure so `/new` no longer exits Codex.
* Add or update regression coverage for the `/new` path.
* Keep the change localized to the TUI/session switching code unless reproduction proves another layer is responsible.

## Acceptance Criteria

* [x] A fresh local Codex TUI session can accept `/new` without process exit.
* [x] Regression coverage locks fresh-session config to the current in-memory config and avoids disk reload.
* [x] `just fmt` is run in `codex-rs` after Rust changes.
* [x] Focused `just test -p codex-tui fresh_session_config_does_not_reload_disk_config` passes.
* [x] `just test -p codex-tui` was run; remaining failures are unrelated existing snapshot drift.
* [x] If lint is run, use `just fix -p codex-tui` before finalizing.

## Definition of Done

* Focused code fix merged into the working tree.
* Regression coverage committed in the relevant TUI test module.
* Required formatting and focused tests completed.
* Trellis spec update decision reviewed.

## Out of Scope

* Redesigning `/new`, `/clear`, `/resume`, or app-server thread lifecycle behavior beyond what is needed for the crash.
* Product documentation updates.
* Changes to sandbox environment variable handling.

## Technical Notes

* Relevant initial files:
  * `codex-rs/tui/src/chatwidget/slash_dispatch.rs`
  * `codex-rs/tui/src/app/event_dispatch.rs`
  * `codex-rs/tui/src/chatwidget/tests/slash_commands.rs`
  * `codex-rs/tui/src/chatwidget/tests/helpers.rs`
* No external research is required; this is a local regression/bugfix task.

## Verification Notes

* Reproduced before the fix with local TUI: `/new` caused `just codex` to exit with signal 6.
* Verified after the fix with local TUI: `/new` no longer exited; `/quit` exited normally with code 0.
* Focused regression test passed:
  * `just test -p codex-tui fresh_session_config_does_not_reload_disk_config`
* Formatting passed:
  * `just fmt`
* Full package test was attempted:
  * `just test -p codex-tui`
  * Result: failed on unrelated snapshot drift in status/history/chatwidget tests, including local version string differences such as `v0.135.0` vs snapshot `v0.0.0`.
