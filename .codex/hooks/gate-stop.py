#!/usr/bin/env python3
"""Codex Stop hook for Trellis inline gate enforcement."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _find_trellis_root(start: Path) -> Path | None:
    cur = start.resolve()
    while cur != cur.parent:
        if (cur / ".trellis").is_dir():
            return cur
        cur = cur.parent
    return None


def _read_hook_input() -> dict:
    try:
        payload = sys.stdin.read()
    except OSError:
        return {}
    if not payload.strip():
        return {}
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _debug(message: str) -> None:
    if os.environ.get("TRELLIS_GATE_DEBUG") == "1":
        print(f"Trellis gate-stop: {message}", file=sys.stderr)


def main() -> int:
    if os.environ.get("TRELLIS_HOOKS") == "0" or os.environ.get("TRELLIS_DISABLE_HOOKS") == "1":
        _debug("hooks disabled by environment")
        return 0

    project_dir = _find_trellis_root(Path.cwd())
    if project_dir is None:
        _debug("no .trellis directory found")
        return 0

    scripts_dir = project_dir / ".trellis" / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    try:
        from common.active_task import resolve_active_task, resolve_context_key, resolve_task_ref  # type: ignore[import-not-found]
        from common.task_gates import check_stop_gates  # type: ignore[import-not-found]
    except Exception as exc:
        _debug(f"failed to import Trellis gate modules: {exc}")
        return 0

    hook_input = _read_hook_input()
    context_key = resolve_context_key(hook_input, platform="codex")
    if not context_key:
        _debug("no Codex session context; bypassing Stop hard gate")
        return 0

    active = resolve_active_task(project_dir, hook_input, platform="codex")
    if active.source_type != "session":
        _debug(f"active task source is {active.source_type}; bypassing Stop hard gate")
        return 0
    if not active.task_path:
        _debug("no active task for Codex session")
        return 0

    task_dir = resolve_task_ref(active.task_path, project_dir)
    if task_dir is None or active.stale or not task_dir.is_dir():
        _debug("active task is stale or missing")
        return 0

    result = check_stop_gates(project_dir, task_dir)
    if result.ok:
        _debug("gate check passed")
        return 0

    print(result.message, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
