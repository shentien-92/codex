---
name: codex-status-line-script
description: Generate, install, preview, or debug scripts for Codex TUI tui.status_line_command custom status lines. Use when a user asks for a Codex status line script, multi-line status line, Claude Code-style statusline customization, or help configuring tui.status_line_command.
---

# Codex Status Line Script

Use this skill to create a script that replaces Codex TUI's built-in status line via `[tui.status_line_command]`.

## Contract

Codex runs the configured command directly, without an implicit shell:

```toml
[tui.status_line_command]
command = ["/absolute/path/to/statusline"]
refresh_interval_ms = 1000
max_lines = 3
```

Behavior to design for:

- Codex writes one JSON payload to stdin and reads stdout.
- The command must finish quickly; Codex times out after 500ms.
- Stdout replaces the whole status line. Empty stdout keeps the previous successful output, or displays empty if none exists.
- Stderr is not rendered; use it only for diagnostics.
- Non-zero exit, timeout, spawn failure, or invalid behavior should degrade gracefully in the script.
- `max_lines` defaults to 3 and is capped at 5 by Codex.
- ANSI SGR color/style sequences are supported; avoid cursor movement, OSC, alternate screen, or terminal control sequences.
- Trusted projects execute the command. Untrusted projects ignore it and fall back to built-in status line items.

## Payload

Input is camelCase JSON with these top-level objects:

```json
{
  "model": {
    "id": "gpt-5.5",
    "displayName": "gpt-5.5 high",
    "reasoningEffort": "high",
    "serviceTier": null
  },
  "workspace": {
    "cwd": "/repo",
    "currentDir": "codex",
    "projectRoot": "/repo"
  },
  "session": {
    "id": "session-id",
    "threadTitle": "Fix status line",
    "codexVersion": "0.135.0"
  },
  "status": {
    "runState": "idle",
    "permissions": "YOLO mode",
    "approvalMode": "never"
  },
  "context": {
    "windowTokens": 272000,
    "usedTokens": 84000,
    "usedPercent": 31,
    "remainingPercent": 69
  },
  "usage": {
    "inputTokens": 1234,
    "outputTokens": 567,
    "totalTokens": 1801
  },
  "git": {
    "branch": "feature/status-line",
    "pullRequestNumber": 123,
    "pullRequestUrl": "https://github.com/openai/codex/pull/123",
    "additions": 42,
    "deletions": 7
  },
  "terminal": {
    "columns": 120,
    "rows": 40
  }
}
```

Every field that looks optional can be `null`. Scripts must tolerate missing keys too, because users may test them with hand-written payloads.

## Workflow

1. Ask only for style preferences that change the output materially: one-line vs multi-line, color level, and which fields matter.
2. Prefer a small dependency-free script in `python3`, `node`, `bash`, or `zsh` depending on the user's environment.
3. Make the script executable and use an absolute path in config examples.
4. Read JSON from stdin with a bounded, simple parser path. On parse failure, print a minimal fallback line and exit 0.
5. Keep output stable in width: truncate long branch/title/path/model fields and avoid wrapping surprises.
6. Print at most the configured line budget. If the user wants rich output, use 2-3 dense lines instead of verbose labels.
7. Preview with `scripts/preview_statusline.py` before finishing.

## Output Patterns

Good compact multi-line layout:

```text
gpt-5.5 high  |  feature/status-line  |  31% ctx
/repo         |  idle  |  YOLO mode    |  PR #123
```

Good single-line layout:

```text
gpt-5.5 high | feature/status-line | 31% ctx | idle | YOLO
```

Avoid:

- Long prose, help text, or keyboard shortcuts.
- Expensive git/network calls inside the script; Codex already sends git/PR fields when available.
- Spinners or animations; refresh is event-driven plus optional interval.
- Writing persistent files unless the user explicitly wants cached external data.

## Preview

After generating a script, run:

```shell
python3 .codex/skills/codex-status-line-script/scripts/preview_statusline.py /absolute/path/to/statusline --max-lines 3
```

Use `--payload path/to/payload.json` when testing a specific case. The helper fails if the script exits non-zero, times out, emits empty output, or exceeds the line cap.
