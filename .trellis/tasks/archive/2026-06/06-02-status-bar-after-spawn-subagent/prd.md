# fix status bar after spawning subagent

## Goal

Fix the TUI footer status bar so it continues to show configured status-line information after a subagent is spawned or a newly attached thread session is configured.

## What I already know

* User report: after spawning a subagent, the status bar does not show any information.
* Status-line footer content is owned by `ChatWidget`/`BottomPane` and recomputed through `ChatWidget::refresh_status_line()`.
* `ChatWidget::handle_thread_session(...)` updates the active thread's model, cwd, service tier, permissions, collaboration state, and status surfaces, but the first-pass inspection indicates it does not explicitly refresh footer status-line content.
* `App::replay_thread_snapshot(...)` already calls `self.refresh_status_line()` after switching/replaying a stored thread snapshot.
* `App::enqueue_primary_thread_session(...)` handles newly attached primary thread sessions and currently does not refresh the status line at the end.
* Likely affected path: app-server/collab subagent thread creation or first attach, where a fresh `ChatWidget` or new thread session state exists before any later event triggers a status-line refresh.

## Assumptions

* Configured status-line items should remain visible after spawning or attaching a subagent thread when those items have renderable values.
* The fix should not change status-line item semantics; unavailable items may still be omitted.
* The fix should be narrow and prefer the existing `refresh_status_line()` orchestration over adding duplicate footer update logic.

## Requirements

* Reproduce or create a focused regression test for a newly configured thread session leaving status-line content empty.
* Fix the thread-session attach/spawn path so status-line content is refreshed after the active session state is available.
* Preserve existing behavior for replayed thread snapshots and normal status-line setup.
* Keep the change localized to TUI session/status-line plumbing unless reproduction proves another layer is responsible.

## Acceptance Criteria

* [x] A configured status line renders after a newly enqueued/app-server thread session.
* [x] A focused regression test fails before the fix and passes after the fix.
* [x] `just fmt` is run in `codex-rs` after Rust changes.
* [x] Focused `just test -p codex-tui enqueue_primary_thread_session_refreshes_status_line` passes.
* [x] `just test -p codex-tui` is run, or any unrelated existing failures are documented.

## Definition of Done

* Focused code fix is committed.
* Regression coverage is committed in the relevant TUI test module.
* Trellis spec update decision is reviewed.
* Task is archived and session journal is recorded after commit.

## Out of Scope

* Redesigning the status-line UI or adding new status-line items.
* Changing status-line command execution semantics.
* Changing subagent spawn protocol, app-server APIs, or collaboration mode behavior unless required by reproduction.
* Fixing unrelated snapshot drift in the broader `codex-tui` test suite.

## Technical Notes

* Relevant files from initial inspection:
  * `codex-rs/tui/src/app/thread_routing.rs`
  * `codex-rs/tui/src/app/session_lifecycle.rs`
  * `codex-rs/tui/src/chatwidget/session_flow.rs`
  * `codex-rs/tui/src/chatwidget/status_controls.rs`
  * `codex-rs/tui/src/chatwidget/status_surfaces.rs`
  * `codex-rs/tui/src/app/tests.rs`
  * `codex-rs/tui/src/chatwidget/tests/status_and_layout.rs`
* Initial hypothesis: `enqueue_primary_thread_session(...)` should refresh the status line after `handle_thread_session(...)`, replay, and pending-event drain, matching the already-present refresh at the end of `replay_thread_snapshot(...)`.

## Verification Notes

* Focused regression test passed:
  * `just test -p codex-tui enqueue_primary_thread_session_refreshes_status_line`
* Formatting passed:
  * `just fmt`
* Full package test was attempted:
  * `just test -p codex-tui`
  * Result: failed on unrelated existing snapshot drift in status/history/chatwidget tests, including local version string differences such as `v0.135.0` vs snapshot `v0.0.0`.
  * Generated `.snap.new` files were removed because they were unrelated to this task.
