# Claude Code Status Line Pattern

## Question

How does Claude Code support custom status lines, and which conventions should influence Codex?

## Source

- Official Claude Code docs: https://code.claude.com/docs/en/statusline

## Findings

Claude Code exposes status-line customization as a shell command configured in settings:

```json
{
  "statusLine": {
    "type": "command",
    "command": "~/.claude/statusline.sh",
    "padding": 2
  }
}
```

The command receives session data as JSON on stdin and Claude Code renders whatever stdout prints. The same docs state that inline shell commands are also supported, not only script paths.

Useful behavior from the model:

- `/statusline` can generate and install a script automatically.
- Manual config supports `type = "command"`, `command`, optional `padding`, optional `refreshInterval`, and optional `hideVimModeIndicator`.
- Updates are event-driven and debounced.
- If another update arrives while the command is still running, the in-flight execution is cancelled.
- Scripts can output multiple lines; each stdout line becomes a separate rendered row.
- ANSI colors and OSC 8 hyperlinks are allowed in output.
- `COLUMNS` and `LINES` are set for the script because the command is not attached directly to the terminal.
- The status-line command is local and does not consume model/API tokens.
- Workspace trust gates command execution because it runs shell code.
- Non-zero exits, empty stdout, or hangs result in no status-line content; slow scripts leave stale content until completion or cancellation.

Notable JSON fields:

- Model: `model.id`, `model.display_name`.
- Workspace: `cwd`, `workspace.current_dir`, `workspace.project_dir`, `workspace.added_dirs`, repo metadata, worktree metadata.
- Cost/duration: total cost, wall-clock duration, API duration, lines added/removed.
- Context window: total input/output tokens, context size, used/remaining percentages, current usage.
- Session: session id/name, transcript path, app version, output style.
- UI/runtime: vim mode, agent info, PR number/url/review state.

Subagent status lines are separate in Claude Code:

- `subagentStatusLine` is another command setting.
- It receives all visible subagent rows as one JSON object and emits JSON lines keyed by task id.
- This is useful precedent but should be out of scope for Codex's first status-line script task unless Codex already has an equivalent agent panel contract ready.

## Mapping to Codex

Good ideas to copy:

- Command source with JSON stdin and stdout-as-rendered-lines.
- Event-driven refresh with debounce plus optional fixed `refresh_interval`.
- Cancellation and timeout to protect TUI responsiveness.
- `COLUMNS`/`LINES` environment variables.
- Multi-line output as a first-class feature.
- Trust/safety treatment equivalent to hooks because this executes shell code.

Ideas to defer:

- Auto-generating scripts from a `/statusline` natural-language command.
- Separate subagent row customization.
- Full cost accounting parity if Codex does not already have the exact same data available.

Open design choices for Codex:

- TOML config shape should be idiomatic for existing Codex config, likely under `[tui.status_line_command]` or `[tui.status_line]` as a typed union replacement. Backward compatibility with current `[tui].status_line = ["..."]` is mandatory.
- JSON input should prefer Codex's existing vocabulary and include enough data for parity with built-in segments first.
- ANSI/OSC parsing should follow existing terminal rendering utilities if available; otherwise plain text can be the MVP with ANSI as a follow-up.
