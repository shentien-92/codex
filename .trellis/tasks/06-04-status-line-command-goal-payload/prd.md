# Status line command goal payload

## Goal

Expose current goal status in tui.status_line_command payload so custom status bars can render goal information when built-in goal UI is hidden.

## Context

- Current custom status bars receive `StatusLineCommandPayload` from `codex-rs/tui/src/status_line_command.rs`.
- The payload already includes model, workspace, session, status, context, usage, git, terminal, and agents.
- Goal state is tracked in `ChatWidget` as `current_goal_status` and rendered as a compact built-in footer indicator only when no collaboration/status bar indicator takes precedence.
- With a command-backed status line enabled, the built-in goal indicator can be visually covered, so scripts need the same goal state in the JSON payload.
- Existing status line scripts must keep working when no goal exists or when goal support is disabled.

## Requirements

- Add a typed `goal` field to `StatusLineCommandPayload`.
- The field should serialize as `null` when no goal is available or the Goals feature is disabled.
- When a goal is available, expose enough data for scripts to build their own compact status:
  - `objective`
  - `status`
  - `tokenBudget`
  - `tokensUsed`
  - `timeUsedSeconds`
  - a compact/display-friendly usage string if one is already derivable without duplicating large UI logic.
- Use camelCase wire names consistent with the existing status line command payload.
- Refresh the command-backed status line when goal updates arrive, including create/edit/status changes and cleared goals.
- Do not change the app-server goal protocol or goal runtime semantics.
- Do not restore or redesign the built-in footer goal indicator; this task only gives custom status bars the data they need.
- Update focused tests for payload serialization and refresh behavior.

## Acceptance Criteria

- [ ] `tui.status_line_command` payload includes a top-level `goal` field.
- [ ] `goal` is `null` when there is no current goal or when the Goals feature is disabled.
- [ ] Active goal payload includes objective, status, token budget, tokens used, time used, and a compact usage string suitable for statusline display.
- [ ] Goal status strings are stable and match the existing app/server goal statuses rather than ad hoc UI labels.
- [ ] A goal update triggers status line command refresh so scripts see new goal state promptly.
- [ ] Clearing a goal clears the payload back to `goal: null` and refreshes the command status line.
- [ ] Existing payload fields and `agents` behavior remain unchanged.
- [ ] Focused `codex-tui` tests cover goal payload present/null and refresh-on-update behavior.
- [ ] `just fmt` is run after Rust changes.
- [ ] Targeted `just test -p codex-tui <goal/statusline tests>` passes.

## Out of Scope

- Changing `/goal` commands, goal lifecycle, persistence, or app-server API.
- Changing the built-in footer layout or the collaboration/statusbar precedence rules.
- Updating Ralph's global `/Users/ralph/.codex/statusline.js` script to consume `goal`; that can be a follow-up once the payload contract exists.

## Notes

- Likely files:
  - `codex-rs/tui/src/status_line_command.rs`
  - `codex-rs/tui/src/chatwidget/status_surfaces.rs`
  - `codex-rs/tui/src/chatwidget/goal_status.rs`
  - `codex-rs/tui/src/chatwidget/settings.rs`
  - `codex-rs/tui/src/app/tests.rs` or focused chatwidget/statusline tests.
