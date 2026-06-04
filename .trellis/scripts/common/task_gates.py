#!/usr/bin/env python3
"""Codex inline task gate markers and readiness checks."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .git import run_git
from .io import read_json, write_json
from .log import Colors, colored
from .paths import FILE_TASK_JSON
from .trellis_config import read_trellis_config

GATES_DIR = ".gates"
GENERATED_BY = "task.py"
_VALID_SPEC_STATUS = {"updated", "not-needed"}
_VALID_COMMIT_STATUS = {"committed", "skipped"}


@dataclass(frozen=True)
class GateCheckResult:
    ok: bool
    message: str = ""


def is_codex_inline(repo_root: Path) -> bool:
    env_mode = os.environ.get("TRELLIS_CODEX_DISPATCH_MODE", "").strip().lower()
    if env_mode == "inline":
        return True
    if env_mode in {"sub-agent", "subagent"}:
        return False

    platform = os.environ.get("TRELLIS_PLATFORM", "").strip().lower()
    has_codex_env = bool(os.environ.get("CODEX_SESSION_ID") or os.environ.get("CODEX_THREAD_ID"))
    is_codex_runtime = platform == "codex" or has_codex_env or _is_codex_hook_process()
    if not is_codex_runtime:
        return False

    config = read_trellis_config(repo_root)
    codex_cfg = config.get("codex") if isinstance(config, dict) else None
    if isinstance(codex_cfg, dict):
        mode = codex_cfg.get("dispatch_mode")
        if isinstance(mode, str) and mode.strip().lower() in {"sub-agent", "subagent"}:
            return False
        if isinstance(mode, str) and mode.strip().lower() == "inline":
            return True

    return True


def _is_codex_hook_process() -> bool:
    script_path = Path(sys.argv[0] or "")
    return ".codex" in script_path.parts


def has_real_prd(task_dir: Path) -> bool:
    prd_path = task_dir / "prd.md"
    try:
        content = prd_path.read_text(encoding="utf-8").strip()
    except (FileNotFoundError, OSError, UnicodeDecodeError):
        return False
    if not content:
        return False

    meaningful_lines = [
        line.strip()
        for line in content.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    non_skeleton = [
        line
        for line in meaningful_lines
        if line not in {"TBD", "TBD.", "- TBD", "- [ ] TBD"}
        and "Keep `prd.md` focused" not in line
        and "Lightweight tasks can remain PRD-only" not in line
        and "For complex tasks" not in line
    ]
    return bool(non_skeleton)


def check_start_gates(repo_root: Path, task_dir: Path, approved: bool) -> GateCheckResult:
    if not is_codex_inline(repo_root):
        return GateCheckResult(True)

    task_json = read_json(task_dir / FILE_TASK_JSON) or {}
    if task_json.get("status") != "planning":
        return GateCheckResult(True)

    if not has_real_prd(task_dir):
        return GateCheckResult(
            False,
            "Gate 2 blocked Codex inline start: prd.md is missing, empty, or still the default TBD skeleton. Run trellis-brainstorm and complete prd.md before starting implementation.",
        )

    if not approved:
        return GateCheckResult(
            False,
            "Gate 3 blocked Codex inline start: implementation approval is required. After artifact review and user approval, run `python3 ./.trellis/scripts/task.py start <task> --approved`.",
        )
    return GateCheckResult(True)


def write_pre_dev_marker(task_dir: Path, specs: list[str], *, force: bool = False, overwrite_reason: str = "") -> bool:
    return _write_marker(
        task_dir,
        "pre-dev",
        {"source": "trellis-before-dev", "specsRead": specs},
        force=force,
        overwrite_reason=overwrite_reason,
    )


def write_changes_marker(
    task_dir: Path,
    has_relevant_changes: bool,
    reason: str,
    *,
    force: bool = False,
    overwrite_reason: str = "",
) -> bool:
    return _write_marker(
        task_dir,
        "changes",
        {"hasRelevantChanges": has_relevant_changes, "reason": reason.strip()},
        force=force,
        overwrite_reason=overwrite_reason,
    )


def write_quality_marker(
    task_dir: Path,
    commands: list[str],
    result: str,
    *,
    force: bool = False,
    overwrite_reason: str = "",
) -> bool:
    cleaned_commands = [cmd.strip() for cmd in commands if cmd.strip()]
    return _write_marker(
        task_dir,
        "quality",
        {"source": "trellis-check", "commands": cleaned_commands, "result": result.strip()},
        force=force,
        overwrite_reason=overwrite_reason,
    )


def write_spec_update_marker(
    task_dir: Path,
    status: str,
    reason: str,
    *,
    force: bool = False,
    overwrite_reason: str = "",
) -> bool:
    return _write_marker(
        task_dir,
        "spec-update",
        {"status": status, "reason": reason.strip()},
        force=force,
        overwrite_reason=overwrite_reason,
    )


def write_commit_marker(
    task_dir: Path,
    status: str,
    reason: str,
    *,
    force: bool = False,
    overwrite_reason: str = "",
) -> bool:
    return _write_marker(
        task_dir,
        "commit",
        {"status": status, "reason": reason.strip()},
        force=force,
        overwrite_reason=overwrite_reason,
    )


def write_worktree_status_marker(
    repo_root: Path,
    task_dir: Path,
    *,
    force: bool = False,
    overwrite_reason: str = "",
) -> bool:
    rc, out, err = run_git(["status", "--short"], cwd=repo_root)
    return _write_marker(
        task_dir,
        "worktree-status",
        {"command": "git status --short", "exitCode": rc, "stdout": out, "stderr": err},
        force=force,
        overwrite_reason=overwrite_reason,
    )


def check_stop_gates(repo_root: Path, task_dir: Path) -> GateCheckResult:
    if not is_codex_inline(repo_root):
        return GateCheckResult(True)
    changes = _valid_marker(task_dir, "changes")
    if not changes:
        return GateCheckResult(
            False,
            "Gate 5 blocked completion: declare whether this task made relevant changes with `python3 ./.trellis/scripts/task.py gate changes <task> --has-relevant-changes true|false --reason <text>`.",
        )
    if changes.get("hasRelevantChanges") is not True:
        return GateCheckResult(True)
    if not _valid_marker(task_dir, "pre-dev"):
        return GateCheckResult(
            False,
            "Gate 5 blocked completion: relevant changes were declared but Gate 4 pre-dev marker is missing. Run trellis-before-dev, then `task.py gate pre-dev <task> --spec <path>...`.",
        )
    quality = _valid_marker(task_dir, "quality")
    if not quality or quality.get("result") != "passed":
        return GateCheckResult(
            False,
            "Gate 5 blocked completion: relevant changes require a passing quality marker. Run trellis-check, then `task.py gate quality <task> --command <cmd> --result passed`.",
        )
    return GateCheckResult(True)


def check_archive_gates(repo_root: Path, task_dir: Path) -> GateCheckResult:
    if not is_codex_inline(repo_root):
        return GateCheckResult(True)

    stop_result = check_stop_gates(repo_root, task_dir)
    if not stop_result.ok:
        return stop_result

    if not _valid_marker(task_dir, "worktree-status"):
        return GateCheckResult(
            False,
            "Gate 6 blocked archive: worktree status marker is missing. Run `python3 ./.trellis/scripts/task.py gate worktree-status <task>` before archive/finish.",
        )

    changes = _valid_marker(task_dir, "changes") or {}
    if changes.get("hasRelevantChanges") is not True:
        return GateCheckResult(True)

    spec_update = _valid_marker(task_dir, "spec-update")
    if not spec_update or spec_update.get("status") not in _VALID_SPEC_STATUS:
        return GateCheckResult(
            False,
            "Gate 6 blocked archive: spec update decision is missing. Run `task.py gate spec-update <task> --status updated|not-needed --reason <text>`.",
        )

    commit = _valid_marker(task_dir, "commit")
    if not commit or commit.get("status") not in _VALID_COMMIT_STATUS:
        return GateCheckResult(
            False,
            "Gate 6 blocked archive: commit decision is missing. Run `task.py gate commit <task> --status committed|skipped --reason <text>`.",
        )
    return GateCheckResult(True)


def print_gate_failure(result: GateCheckResult) -> None:
    if result.message:
        print(colored(result.message, Colors.RED), file=sys.stderr)


def _write_marker(
    task_dir: Path,
    gate: str,
    payload: dict[str, Any],
    *,
    force: bool = False,
    overwrite_reason: str = "",
) -> bool:
    marker_dir = task_dir / GATES_DIR
    marker_dir.mkdir(parents=True, exist_ok=True)
    marker_path = marker_dir / f"{gate}.json"
    reason = overwrite_reason.strip()
    previous_marker = read_json(marker_path) if marker_path.exists() else None
    if marker_path.exists() and not force:
        print(
            colored(
                f"Error: gate marker already exists: {gate}. Use --force --overwrite-reason <text> to replace it.",
                Colors.RED,
            ),
            file=sys.stderr,
        )
        return False
    if marker_path.exists() and not reason:
        print(colored("Error: --overwrite-reason is required with --force", Colors.RED), file=sys.stderr)
        return False

    data = {
        "gate": gate,
        "generatedBy": GENERATED_BY,
        "completedAt": datetime.now(timezone.utc).isoformat(),
    }
    if force:
        data["overwritten"] = True
        data["overwriteReason"] = reason
        if isinstance(previous_marker, dict):
            previous_overwrites = previous_marker.get("overwrites")
            history = list(previous_overwrites) if isinstance(previous_overwrites, list) else []
            snapshot = dict(previous_marker)
            snapshot.pop("overwrites", None)
            history.append(snapshot)
            data["overwrites"] = history
    data.update(payload)
    return write_json(marker_path, data)


def _valid_marker(task_dir: Path, gate: str) -> dict[str, Any] | None:
    data = read_json(task_dir / GATES_DIR / f"{gate}.json")
    if not isinstance(data, dict):
        return None
    if data.get("gate") != gate or data.get("generatedBy") != GENERATED_BY:
        return None
    completed_at = data.get("completedAt")
    if not isinstance(completed_at, str) or not completed_at.strip():
        return None

    if gate == "changes":
        if not isinstance(data.get("hasRelevantChanges"), bool):
            return None
        if not isinstance(data.get("reason"), str) or not data.get("reason", "").strip():
            return None
    elif gate == "quality":
        if data.get("result") != "passed":
            return None
        commands = data.get("commands")
        if not isinstance(commands, list) or not any(isinstance(cmd, str) and cmd.strip() for cmd in commands):
            return None
    elif gate == "worktree-status":
        if data.get("command") != "git status --short":
            return None
        if data.get("exitCode") != 0:
            return None
    elif gate == "spec-update":
        status = data.get("status")
        if status not in _VALID_SPEC_STATUS:
            return None
        if status == "not-needed" and not str(data.get("reason") or "").strip():
            return None
    elif gate == "commit":
        status = data.get("status")
        if status not in _VALID_COMMIT_STATUS:
            return None
        if status == "skipped" and not str(data.get("reason") or "").strip():
            return None
    elif gate == "pre-dev":
        specs = data.get("specsRead")
        if specs is not None and not isinstance(specs, list):
            return None
    return data
