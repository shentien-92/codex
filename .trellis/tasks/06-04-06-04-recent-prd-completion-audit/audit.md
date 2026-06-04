# Recent PRD Completion Audit

Scope: archived Trellis tasks under `.trellis/tasks/archive/2026-06`.

## Summary

No newly actionable missed code feature was found beyond the MCP startup nonblocking gap that was completed and archived in `.trellis/tasks/archive/2026-06/06-04-mcp-startup-nonblocking-gap-completion`.

Several 2026-06-02 statusline/subagent PRDs are intermediate iterations. Their older acceptance criteria are intentionally superseded by later Ralph-confirmed direction, especially removing agent-switch hints and avoiding statusline running/done state as a behavior source. Those are recorded as superseded rather than open gaps.

## Audit Table

| Task | Status | Evidence / Notes |
| --- | --- | --- |
| `05-29-mcp-startup-nonblocking-prd` | gap completed by follow-up | Original PRD was incomplete. Follow-up task `06-04-mcp-startup-nonblocking-gap-completion` added manager/resource/metadata/connector/plugin fixes plus session/subagent coverage. Evidence: `codex-rs/core/tests/suite/mcp_startup_nonblocking.rs`, `codex-rs/codex-mcp/src/connection_manager_tests.rs`, follow-up `quality.md`, and work commit `227329efb`. |
| `06-01-codex-status-line-customization-prd` | pass | Current code has command-backed status line runner and payload: `codex-rs/tui/src/status_line_command.rs`, `codex-rs/tui/src/chatwidget/status_surfaces.rs`, `codex-rs/tui/src/bottom_pane/footer.rs`. Tests cover line caps, ANSI parsing, trusted/untrusted behavior, and payload. Evidence commit in history: `af0b3d872 feat(tui): add status line command and MCP polish`. |
| `06-01-local-codex-status-line-preview` | pass, no PRD artifact | Archived task has no `prd.md`, so it is outside PRD acceptance audit. Evidence of implemented script exists at `.codex/statusline.js`; global configured script exists at `/Users/ralph/.codex/statusline.js`. |
| `06-02-add-agent-switch-hint-to-status-bar` | superseded | Later PRD `06-02-simplify-agent-status-line-copy` explicitly required removing the newly added built-in footer switch hint. Current absence of the hint is intentional, not a missed feature. |
| `06-02-agents-status-count-zero` | pass, later narrowed | Payload includes `agents.total/current/items`: `codex-rs/tui/src/status_line_command.rs`. Tests include `collab_receiver_notification_updates_status_line_command_agents` and `subagent_notification_updates_status_line_command_agents`. Later PRDs narrowed the user-visible script to Trellis-only/global compact output. |
| `06-02-fix-mac-agent-view-shortcut-navigation` | superseded by rollback | The task's navigation-sync requirement was later rolled back by `06-02-separate-subagent-status-from-thread-closed-state` to avoid coupling statusline notification state to agent navigation. Current navigation code still has independent shortcut/backfill support in `codex-rs/tui/src/app/session_lifecycle.rs` and `codex-rs/tui/src/app/input.rs`. |
| `06-02-fix-subagent-completed-status-line-state` | superseded by rollback | Later task `06-02-separate-subagent-status-from-thread-closed-state` removed running/done statusline display as a product requirement. Current script no longer depends on completed/running agent state. |
| `06-02-link-local-codex-release-build` | pass/manual | PRD has checked acceptance notes showing release build, symlink, npm uninstall, and `codex --version` verification. No source code change expected. |
| `06-02-local-codex-new-crash` | pass | PRD verification notes record reproduction and focused test. Current code uses `fresh_session_config()` instead of disk reload in `codex-rs/tui/src/app/session_lifecycle.rs`; regression test `fresh_session_config_does_not_reload_disk_config` exists in `codex-rs/tui/src/app/tests.rs`. |
| `06-02-record-local-codex-debug-verification-command` | pass | Trellis spec exists at `.trellis/spec/codex/frontend/quality-guidelines.md` and records local debug verification workflow. |
| `06-02-separate-subagent-status-from-thread-closed-state` | pass/current direction | Current app statusline payload can count agents, but global statusline output is Trellis-focused and does not use agent running/done state. This task intentionally supersedes earlier statusline-state coupling. |
| `06-02-simplify-agent-status-line-copy` | superseded by later Trellis compact script | The immediate agent-copy requirement was later replaced by `06-02-statusline-trellis-compact`, which no longer displays an agent segment in the global script. This is an intentional product direction change. |
| `06-02-status-bar-after-spawn-subagent` | pass | Regression test `enqueue_primary_thread_session_refreshes_status_line` exists in `codex-rs/tui/src/app/tests.rs`. Current code refreshes status line after thread attach path. Evidence commit: `4b3001492 fix(tui): refresh status line after thread attach`. |
| `06-02-statusline-trellis-compact` | pass | Global configured script `/Users/ralph/.codex/statusline.js` renders compact Trellis line. Simulated payload output: `[CX] Recent PRD completion audit · xiuran · 1 task(s) · ralph/rust-v0.135.0-custom`. Repo copy `.codex/statusline.js` also contains compact Trellis logic. |
| `06-03-sync-internal-gitlab-npm` | partial by explicit scope | GitLab sync acceptance is checked in the PRD. `npm publish` acceptance remains unchecked because publish was not actually executed; PRD notes explicitly say "npm publish 未实际执行". This is not a code-missed feature; it is an intentionally unexecuted external release step. |
| `06-04-mcp-startup-nonblocking-gap-completion` | pass | Archived follow-up task has quality evidence and commit `227329efb`; focused tests passed: `just test -p codex-core mcp_startup_nonblocking`, earlier `just test -p codex-mcp`, and `just fix -p codex-core`. |

## Commands / Evidence Checks

- Listed archived June tasks with `python3 ./.trellis/scripts/task.py list-archive 2026-06`.
- Enumerated PRDs with `find .trellis/tasks -path '*/prd.md' -maxdepth 5`.
- Searched implementation/test evidence with `rg` over `codex-rs/tui/src`, `codex-rs/core/src`, `codex-rs/cli/src`, and `codex-rs/codex-mcp/src`.
- Previewed the actual global statusline script with a simulated payload:

```text
gpt-5 high · workspace-wri… · Ready · ctx 37% [▰▰▰▰▱▱▱▱▱▱] · codex
  [CX] Recent PRD completion audit · xiuran · 1 task(s) · ralph/rust-v0.135.0-custom
```

## Follow-Up Tasks

None required from this audit.
