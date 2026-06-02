# Diagnose Agents Status Count Stuck At Zero

## Problem

Ralph's local status line script shows `agents 0` after spawning subagents. The spawned agents exist, but the custom `tui.status_line_command` receives no agent data in its JSON payload, so the script falls back to zero.

## Findings

- `~/.codex/statusline.js` reads `data.agents.total`, `data.agents.current`, and `data.agents.items[]`.
- `codex-rs/tui/src/status_line_command.rs` does not define an `agents` payload field.
- `App::upsert_agent_picker_thread` updates the TUI agent navigation cache, but that state is not mirrored into the status line command payload.
- Subagents spawned through the outer agent API can also arrive as `<subagent_notification>` messages rather than `CollabAgentToolCall` notifications, so the status line must parse both sources.

## Requirements

- Expose subagent summary data through the custom status line command payload.
- Keep the payload compatible with Ralph's existing script shape: `agents.total`, `agents.current`, and `agents.items[]`.
- Count only non-primary threads as agents.
- Refresh the status line command when agent metadata or liveness changes.
- Add focused regression coverage.

## Acceptance

- After spawning a subagent, the status line command receives `agents.total > 0`.
- Closed subagent threads report a completed status; open subagent threads report a running status.
- Existing built-in status line behavior remains unchanged.
