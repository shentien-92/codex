#!/usr/bin/env python3
"""Trellis per-turn breadcrumb hook (UserPromptSubmit / BeforeAgent equivalent).

Runs on every user prompt. Resolves the active task through Trellis'
session-aware active task resolver and emits a short <workflow-state>
block reminding the main AI what task is active and its expected flow.

The emitted ``hookEventName`` field is platform-aware: most hosts expect
``UserPromptSubmit`` (Claude Code naming, also accepted by Cursor / Qoder /
CodeBuddy / Droid / Codex / Copilot wiring), but Gemini CLI 0.40.x renamed
its per-turn event to ``BeforeAgent`` and its schema validator rejects the
legacy name. ``_detect_platform`` picks the right value at runtime.
Breadcrumb text is pulled exclusively from workflow.md
[workflow-state:STATUS] tag blocks — workflow.md is the single source of
truth. There are no fallback dicts in this script: when workflow.md is
missing or a tag is absent, the breadcrumb degrades to a generic
"Refer to workflow.md for current step." line so users see (and fix)
the broken state instead of the hook silently masking it.

Shared across all hook-capable platforms (Claude, Cursor, Codex, Qoder,
CodeBuddy, Droid, Gemini, Copilot). Kiro is not wired (no per-turn
hook entry point). Written to each platform's hooks directory via
writeSharedHooks() at init time.

Silent exit 0 cases (no output):
  - No .trellis/ directory found (not a Trellis project)
  - task.json malformed or missing status
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# Force UTF-8 on stdin/stdout/stderr on Windows. Default codepage there is
# cp936 / cp1252 / etc. — non-ASCII content (Chinese task names, prd snippets)
# both in stdin (hook payload from host CLI) and stdout (our emitted blocks)
# raises UnicodeDecodeError / UnicodeEncodeError. Equivalent to `python -X utf8`
# but applied per-stream so we don't depend on host CLI's command wiring.
if sys.platform.startswith("win"):
    import io as _io
    for _stream_name in ("stdin", "stdout", "stderr"):
        _stream = getattr(sys, _stream_name, None)
        if _stream is None:
            continue
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
            except Exception:
                pass
        elif hasattr(_stream, "detach"):
            try:
                setattr(sys, _stream_name, _io.TextIOWrapper(_stream.detach(), encoding="utf-8", errors="replace"))
            except Exception:
                pass
from typing import Optional


# Bootstrap notice for Codex while the session has no active task. Codex does not
# get the full SessionStart overview; this short reminder points the main session
# at the start skill once and leaves the per-turn state block compact.
CODEX_NO_TASK_BOOTSTRAP_NOTICE = """<trellis-bootstrap>
If you have not already loaded Trellis context this session, read the `trellis-start` skill once.
</trellis-bootstrap>"""
TRELLIS_VERSION_CHECK_CACHE = ".trellis/.runtime/trellis-version-check.json"
TRELLIS_VERSION_CHECK_TTL_SECONDS = 24 * 60 * 60


def _parse_version(value: str) -> tuple[int, int, int, str, int] | None:
    match = re.search(r"(\d+)\.(\d+)\.(\d+)(?:-([A-Za-z]+)\.(\d+))?", value)
    if not match:
        return None
    return (
        int(match.group(1)),
        int(match.group(2)),
        int(match.group(3)),
        match.group(4) or "",
        int(match.group(5) or 0),
    )


def _compare_versions(left: str, right: str) -> int:
    left_parsed = _parse_version(left)
    right_parsed = _parse_version(right)
    if left_parsed is None or right_parsed is None:
        return 0

    for left_part, right_part in zip(left_parsed[:3], right_parsed[:3]):
        if left_part != right_part:
            return 1 if left_part > right_part else -1

    left_tag, right_tag = left_parsed[3], right_parsed[3]
    if left_tag != right_tag:
        if not left_tag:
            return 1
        if not right_tag:
            return -1
        return 1 if left_tag > right_tag else -1

    if left_parsed[4] == right_parsed[4]:
        return 0
    return 1 if left_parsed[4] > right_parsed[4] else -1


def _release_channel(version: str) -> str:
    if "-beta." in version:
        return "beta"
    if "-rc." in version:
        return "rc"
    if "-alpha." in version:
        return "alpha"
    return "latest"


def _run_version_command(project_dir: Path, command: list[str]) -> str:
    env = os.environ.copy()
    env["TRELLIS_SKIP_CLI_UPDATE_CHECK"] = "1"
    env.setdefault("NO_COLOR", "1")
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=3,
            cwd=str(project_dir),
            env=env,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
        return ""
    if result.returncode != 0:
        return ""
    return "\n".join(part for part in (result.stdout, result.stderr) if part)


def _extract_version(output: str) -> str:
    matches = re.findall(r"\d+\.\d+\.\d+(?:-[A-Za-z]+\.\d+)?", output)
    return matches[-1] if matches else ""


def _read_cached_latest_version(root: Path, channel: str) -> str:
    cache_path = root / TRELLIS_VERSION_CHECK_CACHE
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return ""
    if not isinstance(data, dict):
        return ""
    if data.get("channel") != channel:
        return ""
    checked_at = data.get("checkedAt")
    if not isinstance(checked_at, (int, float)):
        return ""
    if time.time() - float(checked_at) > TRELLIS_VERSION_CHECK_TTL_SECONDS:
        return ""
    latest = data.get("latestVersion")
    return latest if isinstance(latest, str) else ""


def _write_cached_latest_version(root: Path, channel: str, latest_version: str) -> None:
    cache_path = root / TRELLIS_VERSION_CHECK_CACHE
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(
                {
                    "checkedAt": time.time(),
                    "channel": channel,
                    "latestVersion": latest_version,
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
    except OSError:
        return


def _latest_trellis_version(project_dir: Path, channel: str) -> str:
    cached = _read_cached_latest_version(project_dir, channel)
    if cached:
        return cached
    output = _run_version_command(
        project_dir,
        ["npm", "view", f"@qunhe/trellis@{channel}", "version", "--silent"],
    )
    latest = _extract_version(output)
    _write_cached_latest_version(project_dir, channel, latest)
    return latest


def _build_trellis_cli_version_warning(project_dir: Path) -> str:
    local_version = _extract_version(
        _run_version_command(project_dir, ["trellis", "--version"])
    )
    if not local_version:
        return ""
    channel = _release_channel(local_version)
    latest_version = _latest_trellis_version(project_dir, channel)
    if not latest_version or _compare_versions(latest_version, local_version) <= 0:
        return ""

    install_target = channel if channel != "latest" else "latest"
    return "\n".join(
        [
            "本机 Trellis CLI 落后，当前 managed skill 检测结果不完整。",
            f"- 本机 CLI: {local_version}",
            f"- 远端 {channel}: {latest_version}",
            f"- 建议马上运行: `npm install -g @qunhe/trellis@{install_target}`",
            "- 升级后立即运行: `trellis update --create-new`",
            "除非用户明确要求跳过，否则开始实现前应优先处理。",
        ]
    )


def _build_managed_skill_update_warning(project_dir: Path) -> str:
    version_warning = _build_trellis_cli_version_warning(project_dir)
    env = os.environ.copy()
    env["TRELLIS_SKIP_CLI_UPDATE_CHECK"] = "1"
    env.setdefault("NO_COLOR", "1")
    try:
        result = subprocess.run(
            ["trellis", "skill-updates", "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=3,
            cwd=str(project_dir),
            env=env,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
        if not version_warning:
            return ""
        summary = {}
    else:
        if result.returncode != 0:
            if not version_warning:
                return ""
            summary = {}
        else:
            try:
                summary = json.loads(result.stdout)
            except json.JSONDecodeError:
                if not version_warning:
                    return ""
                summary = {}

    if not isinstance(summary, dict):
        summary = {}

    update_available = int(summary.get("updateAvailable") or 0)
    missing = int(summary.get("missing") or 0)
    locally_modified = int(summary.get("locallyModified") or 0)
    if update_available == 0 and missing == 0 and locally_modified == 0 and not version_warning:
        return ""

    if version_warning:
        return "\n".join(
            [
                "开始实现用户需求、创建/启动 Trellis task、或编辑代码前，必须先把下面的 Trellis CLI 更新状态告诉用户。",
                "不要把当前本机 managed skill 检测结果当成最终结论；本机 CLI 落后时它是不完整的。",
                "建议马上升级全局 Trellis，并用安全方式更新项目模板。",
                "",
                "全局 Trellis CLI 版本：",
                *version_warning.splitlines(),
            ]
        )

    lines = [
        "开始实现用户需求、创建/启动 Trellis task、或编辑代码前，必须先把下面的 Trellis managed skill 状态告诉用户。",
        "不要静默忽略这个提醒；如果用户选择继续，可以先不更新。",
        "建议询问是否先运行 `trellis update --create-new` 检查并安全应用更新。",
        "",
        "当前 managed skill 检测结果：",
        f"- 可更新: {update_available}",
        f"- 缺失托管文件: {missing}",
        f"- 本地已修改: {locally_modified}",
    ]

    details = summary.get("details")
    if isinstance(details, list):
        interesting = [
            d for d in details
            if isinstance(d, dict) and d.get("status") != "up_to_date"
        ][:5]
        if interesting:
            lines.append("")
            lines.append("示例：")
            for item in interesting:
                status = item.get("status") or "unknown"
                item_path = item.get("path") or "(unknown path)"
                lines.append(f"- {status}: {item_path}")

    return "\n".join(lines)


def _managed_skill_warning_session_key(input_data: dict) -> str:
    """Return a stable conversation key so Codex prompt hooks warn once.

    Codex runs this hook on every user prompt. The managed-skill warning is
    intentionally strong, so repeating it after the user says "continue" is
    noisy. Prefer host-provided session/conversation ids, then transcript paths.
    If the host provides none, return an empty key and keep the old behavior.
    """
    for key in (
        "session_id",
        "sessionId",
        "conversation_id",
        "conversationId",
        "conversationID",
        "transcript_path",
        "transcriptPath",
        "transcript",
    ):
        value = input_data.get(key)
        if isinstance(value, str) and value.strip():
            return f"{key}:{value.strip()}"
    return ""


def _should_emit_managed_skill_update_warning_once(root: Path, input_data: dict) -> bool:
    session_key = _managed_skill_warning_session_key(input_data)
    if not session_key:
        return True

    marker_path = root / ".trellis" / ".runtime" / "managed-skill-warning-sessions.json"
    try:
        marker_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return True

    try:
        data = json.loads(marker_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        data = {}
    if not isinstance(data, dict):
        data = {}

    warned = data.get("warned")
    if not isinstance(warned, list):
        warned = []
    if session_key in warned:
        return False

    warned.append(session_key)
    data["warned"] = warned[-50:]
    try:
        marker_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError:
        return True
    return True


# ---------------------------------------------------------------------------
# CWD-robust Trellis root discovery (fixes hook-path-robustness for this hook)
# ---------------------------------------------------------------------------

def find_trellis_root(start: Path) -> Optional[Path]:
    """Walk up from start to find directory containing .trellis/.

    Handles CWD drift: subdirectory launches, monorepo packages, etc.
    Returns None if no .trellis/ found (silent no-op).
    """
    cur = start.resolve()
    while cur != cur.parent:
        if (cur / ".trellis").is_dir():
            return cur
        cur = cur.parent
    return None


# ---------------------------------------------------------------------------
# Active task discovery
# ---------------------------------------------------------------------------

def _detect_platform(input_data: dict) -> str | None:
    if isinstance(input_data.get("cursor_version"), str):
        return "cursor"
    env_map = {
        "CLAUDE_PROJECT_DIR": "claude",
        "CURSOR_PROJECT_DIR": "cursor",
        "CODEBUDDY_PROJECT_DIR": "codebuddy",
        "FACTORY_PROJECT_DIR": "droid",
        "GEMINI_PROJECT_DIR": "gemini",
        "QODER_PROJECT_DIR": "qoder",
        "KIRO_PROJECT_DIR": "kiro",
        "COPILOT_PROJECT_DIR": "copilot",
    }
    for env_name, platform in env_map.items():
        if os.environ.get(env_name):
            return platform
    script_parts = set(Path(sys.argv[0]).parts)
    if ".claude" in script_parts:
        return "claude"
    if ".cursor" in script_parts:
        return "cursor"
    if ".codex" in script_parts:
        return "codex"
    if ".gemini" in script_parts:
        return "gemini"
    if ".qoder" in script_parts:
        return "qoder"
    if ".codebuddy" in script_parts:
        return "codebuddy"
    if ".factory" in script_parts:
        return "droid"
    if ".kiro" in script_parts:
        return "kiro"
    return None


def _resolve_active_task(root: Path, input_data: dict):
    scripts_dir = root / ".trellis" / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from common.active_task import resolve_active_task  # type: ignore[import-not-found]

    return resolve_active_task(root, input_data, platform=_detect_platform(input_data))


def get_active_task(root: Path, input_data: dict) -> Optional[tuple[str, str, str]]:
    """Return (task_id, status, source) from the current active task."""
    active = _resolve_active_task(root, input_data)
    if not active.task_path:
        return None

    task_dir = Path(active.task_path)
    if not task_dir.is_absolute():
        task_dir = root / task_dir
    if active.stale:
        return task_dir.name, f"stale_{active.source_type}", active.source

    task_json = task_dir / "task.json"
    if not task_json.is_file():
        return None
    try:
        data = json.loads(task_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    task_id = data.get("id") or task_dir.name
    status = data.get("status", "")
    if not isinstance(status, str) or not status:
        return None
    return task_id, status, active.source


# ---------------------------------------------------------------------------
# Breadcrumb loading: parse workflow.md, fall back to hardcoded defaults
# ---------------------------------------------------------------------------

# Supports STATUS values with letters, digits, underscores, hyphens
# (so "in-review" / "blocked-by-team" work alongside "in_progress").
_TAG_RE = re.compile(
    r"\[workflow-state:([A-Za-z0-9_-]+)\]\s*\n(.*?)\n\s*\[/workflow-state:\1\]",
    re.DOTALL,
)

def load_breadcrumbs(root: Path) -> dict[str, str]:
    """Parse workflow.md for [workflow-state:STATUS] blocks.

    Returns {status: body_text}. workflow.md is the single source of
    truth — there are no fallback dicts in this script. Missing tags
    (or a missing/unreadable workflow.md) fall back to a generic line
    in build_breadcrumb so users see the broken state and fix
    workflow.md, rather than the hook silently masking the issue.
    """
    workflow = root / ".trellis" / "workflow.md"
    if not workflow.is_file():
        return {}
    try:
        content = workflow.read_text(encoding="utf-8")
    except OSError:
        return {}

    result: dict[str, str] = {}
    for match in _TAG_RE.finditer(content):
        status = match.group(1)
        body = match.group(2).strip()
        if body:
            result[status] = body
    return result


def _read_trellis_config(root: Path) -> dict:
    """Load .trellis/config.yaml via the bundled trellis_config helper.

    The helper lives in .trellis/scripts/common; the hook lives outside the
    scripts tree, so we extend sys.path before importing.
    """
    scripts_dir = root / ".trellis" / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    try:
        from common.trellis_config import read_trellis_config  # type: ignore[import-not-found]
    except Exception:
        return {}
    try:
        return read_trellis_config(root)
    except Exception:
        return {}


def _codex_mode_banner(config: dict) -> str:
    """Emit a `<codex-mode>` banner for the additionalContext payload.

    Reads `codex.dispatch_mode` from .trellis/config.yaml; defaults to
    `inline` when missing or invalid because Codex sub-agents run with
    `fork_turns="none"` isolation and can't inherit the parent session's
    task context. The banner makes the active mode explicit to Codex AI
    per turn, complementing the workflow-state body which is per-status.
    Mode tells AI which dispatch protocol to follow; workflow-state tells
    AI what step it's at.
    """
    mode = "inline"
    if isinstance(config, dict):
        codex_cfg = config.get("codex")
        if isinstance(codex_cfg, dict):
            cfg_mode = codex_cfg.get("dispatch_mode")
            if cfg_mode in ("inline", "sub-agent"):
                mode = cfg_mode
    if mode == "sub-agent":
        meaning = "sub-agent"
    else:
        meaning = "inline"
    return f"<codex-mode>{meaning}</codex-mode>"


def resolve_breadcrumb_key(
    status: str, platform: str | None, config: dict
) -> str:
    """Pick the breadcrumb tag key based on Codex dispatch_mode.

    Codex defaults to ``inline`` because sub-agents run with ``fork_turns="none"``
    isolation and can't inherit the parent session's task context. Users can
    opt into ``codex.dispatch_mode: sub-agent`` in ``.trellis/config.yaml``
    to use the parallel ``<status>-inline`` tag → ``<status>`` flip. Invalid
    or missing values fall back to inline.

    Non-codex platforms return the plain status unchanged.
    """
    if platform == "codex":
        mode = "inline"
        if isinstance(config, dict):
            codex_cfg = config.get("codex")
            if isinstance(codex_cfg, dict):
                cfg_mode = codex_cfg.get("dispatch_mode")
                if cfg_mode in ("inline", "sub-agent"):
                    mode = cfg_mode
        return f"{status}-inline" if mode == "inline" else status
    return status


def build_breadcrumb(
    task_id: Optional[str],
    status: str,
    templates: dict[str, str],
    source: str | None = None,
    breadcrumb_key: str | None = None,
) -> str:
    """Build the <workflow-state>...</workflow-state> block.

    - Known status (tag present in workflow.md) → detailed template body
    - Unknown status (no tag, or workflow.md missing) → generic
      "Refer to workflow.md for current step." line
    - `no_task` pseudo-status (task_id is None) → header omits task info
    """
    lookup_key = breadcrumb_key or status
    body = templates.get(lookup_key)
    if body is None and lookup_key != status:
        body = templates.get(status)
    if body is None:
        body = "Refer to workflow.md for current step."
    header = f"Status: {status}" if task_id is None else f"Task: {task_id} ({status})"
    return f"<workflow-state>\n{header}\n{body}\n</workflow-state>"


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

def main() -> int:
    if os.environ.get("TRELLIS_HOOKS") == "0" or os.environ.get("TRELLIS_DISABLE_HOOKS") == "1":
        return 0

    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        data = {}

    cwd_str = data.get("cwd") or os.getcwd()
    cwd = Path(cwd_str)

    root = find_trellis_root(cwd)
    if root is None:
        return 0  # not a Trellis project

    templates = load_breadcrumbs(root)
    platform = _detect_platform(data)
    config = _read_trellis_config(root)
    task = get_active_task(root, data)
    if task is None:
        # No active task — still emit a breadcrumb nudging AI toward
        # trellis-brainstorm + task.py create when user describes real work.
        no_task_key = resolve_breadcrumb_key("no_task", platform, config)
        breadcrumb = build_breadcrumb(
            None, "no_task", templates, breadcrumb_key=no_task_key
        )
    else:
        task_id, status, source = task
        status_key = resolve_breadcrumb_key(status, platform, config)
        source_for_breadcrumb = None if platform == "codex" else source
        breadcrumb = build_breadcrumb(
            task_id, status, templates, source_for_breadcrumb, breadcrumb_key=status_key
        )
    if platform == "codex":
        parts: list[str] = []
        skill_update_warning = ""
        if _should_emit_managed_skill_update_warning_once(root, data):
            skill_update_warning = _build_managed_skill_update_warning(root)
        if skill_update_warning:
            parts.append(
                f"<managed-skill-update-warning>\n{skill_update_warning}\n"
                "</managed-skill-update-warning>"
            )
        if task is None:
            parts.append(CODEX_NO_TASK_BOOTSTRAP_NOTICE)
        parts.append(_codex_mode_banner(config))
        parts.append(breadcrumb)
        breadcrumb = "\n\n".join(parts)

    # Gemini CLI 0.40.x rejects "UserPromptSubmit" — its per-turn event is
    # named "BeforeAgent". Other platforms (Claude/Cursor/Qoder/CodeBuddy/
    # Droid/Codex/Copilot) accept the original Claude-style name.
    hook_event_name = (
        "BeforeAgent" if platform == "gemini" else "UserPromptSubmit"
    )

    output = {
        "hookSpecificOutput": {
            "hookEventName": hook_event_name,
            "additionalContext": breadcrumb,
        }
    }
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
