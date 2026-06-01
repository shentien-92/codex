#!/usr/bin/env python3
"""Preview a Codex status line command with a representative payload."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


DEFAULT_PAYLOAD = {
    "model": {
        "id": "gpt-5.5",
        "displayName": "gpt-5.5 high",
        "reasoningEffort": "high",
        "serviceTier": None,
    },
    "workspace": {
        "cwd": "/Users/ralph/Coding/shenty/codex",
        "currentDir": "codex",
        "projectRoot": "/Users/ralph/Coding/shenty/codex",
    },
    "session": {
        "id": "preview-session",
        "threadTitle": "Preview status line script",
        "codexVersion": "0.135.0",
    },
    "status": {
        "runState": "idle",
        "permissions": "YOLO mode",
        "approvalMode": "never",
    },
    "context": {
        "windowTokens": 272000,
        "usedTokens": 84000,
        "usedPercent": 31,
        "remainingPercent": 69,
    },
    "usage": {
        "inputTokens": 1234,
        "outputTokens": 567,
        "totalTokens": 1801,
    },
    "git": {
        "branch": "feature/status-line",
        "pullRequestNumber": 123,
        "pullRequestUrl": "https://github.com/openai/codex/pull/123",
        "additions": 42,
        "deletions": 7,
    },
    "terminal": {
        "columns": 120,
        "rows": 40,
    },
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", nargs="+", help="status line command argv")
    parser.add_argument("--payload", type=Path, help="JSON payload file")
    parser.add_argument("--max-lines", type=int, default=3)
    parser.add_argument("--timeout-ms", type=int, default=500)
    args = parser.parse_args()

    payload = DEFAULT_PAYLOAD
    if args.payload:
        payload = json.loads(args.payload.read_text())

    completed = subprocess.run(
        args.command,
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=args.timeout_ms / 1000,
        check=False,
    )

    if completed.returncode != 0:
        sys.stderr.write(completed.stderr)
        print(f"status line command exited {completed.returncode}", file=sys.stderr)
        return 1

    output = completed.stdout.rstrip("\r\n")
    if not output.strip():
        print("status line command emitted empty output", file=sys.stderr)
        return 1

    lines = output.splitlines()
    if len(lines) > args.max_lines:
        print(
            f"status line command emitted {len(lines)} lines; max is {args.max_lines}",
            file=sys.stderr,
        )
        return 1

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
