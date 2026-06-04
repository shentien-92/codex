#!/usr/bin/env python3
"""Project-local telemetry recorder for Trellis hook-capable platforms.

This hook is intentionally side-effect-light:
- Reads hook stdin JSON when available
- Appends a compact JSON line into `.trellis/.runtime/telemetry/hook-events.jsonl`
- Optionally POSTs recognized `skill_call` / `mcp_call` events to a configured
  remote endpoint
- Never prints to stdout/stderr during normal prompt/tool execution
- Prints a concise Moon share result only for session-end reporting
- Never modifies hook inputs or host behavior

Remote reporting local config:
- `.trellis/.runtime/telemetry/config.json`
- Gitignored runtime-only file for tokens and local overrides
- Endpoint paths / protocol stay built into the hook for enterprise parity

Example config:
{
  "enabled": true,
  "token": "replace-me",
  "timeoutMs": 1500,
  "userId": "trellis",
  "operator": "trellis"
}

The script is shared across platforms; hook configs pass a coarse event kind
(`session`, `prompt`, `tool`, `agent_spawn`) as argv[1] so the recorder can
classify the event even when platforms use different hook event names.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_REMOTE_TIMEOUT_MS = 1500
DEFAULT_REMOTE_CONFIG_PATH = ".trellis/.runtime/telemetry/config.json"
DEFAULT_CALL_STATE_PATH = ".trellis/.runtime/telemetry/call-state.json"
DEFAULT_REMOTE_BASE_URL = (
    "http://qaopenapi-platform-admin-prod.k8s-xiasha.qunhequnhe.com"
)
DEFAULT_REMOTE_TOKEN_HEADER = "qaOpenApiToken"
DEFAULT_REMOTE_REPORT_PATH = "/renren-admin/metric/digitalemployeemetriclogs/report"
DEFAULT_REMOTE_ROLE = "rd_general_staff"
DEFAULT_REMOTE_USER_ID = "trellis"
DEFAULT_REMOTE_OPERATOR = "trellis"
DEFAULT_REMOTE_METRIC_TYPE = "CODING"
DEFAULT_REMOTE_SCENARIO_TYPE = "SINGLE"
DEFAULT_REMOTE_DOMAIN = "tool"
DEFAULT_SESSION_SHARE_STATUS_PATH = (
    ".trellis/.runtime/telemetry/session-share.jsonl"
)
DEFAULT_SESSION_SHARE_TIMEOUT_MS = 8000
DEFAULT_SESSION_SHARE_COMMAND = "npx"
DEFAULT_SESSION_SHARE_ARGS = [
    "-y",
    "@qunhe/moon-cli@latest",
    "share",
    "claude-code-session",
]
ENV_SESSION_KEYS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("claude", ("CLAUDE_SESSION_ID", "CLAUDE_CODE_SESSION_ID")),
    ("codex", ("CODEX_SESSION_ID", "CODEX_THREAD_ID")),
    ("cursor", ("CURSOR_SESSION_ID",)),
    ("opencode", ("OPENCODE_SESSION_ID", "OPENCODE_SESSIONID", "OPENCODE_RUN_ID")),
    ("gemini", ("GEMINI_SESSION_ID",)),
    ("droid", ("FACTORY_SESSION_ID", "DROID_SESSION_ID")),
    ("qoder", ("QODER_SESSION_ID",)),
    ("codebuddy", ("CODEBUDDY_SESSION_ID",)),
    ("kiro", ("KIRO_SESSION_ID",)),
    ("copilot", ("COPILOT_SESSION_ID", "COPILOT_SESSIONID")),
    ("pi", ("PI_SESSION_ID", "PI_SESSIONID")),
)


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
                setattr(
                    sys,
                    _stream_name,
                    _io.TextIOWrapper(
                        _stream.detach(), encoding="utf-8", errors="replace"
                    ),
                )
            except Exception:
                pass


def _find_trellis_root(start: Path) -> Path | None:
    cur = start.resolve()
    while cur != cur.parent:
        if (cur / ".trellis").is_dir():
            return cur
        cur = cur.parent
    return None


def _detect_platform(input_data: dict[str, Any]) -> str | None:
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
    if ".github" in script_parts:
        return "copilot"
    return None


def _truncate(value: str, limit: int = 160) -> str:
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _string(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _first_string(*values: Any) -> str:
    for value in values:
        text = _string(value)
        if text:
            return text
    return ""


def _extract_prompt_preview(input_data: dict[str, Any]) -> str:
    candidates = [
        input_data.get("prompt"),
        input_data.get("user_message"),
        input_data.get("toolArgs"),
    ]
    tool_input = input_data.get("tool_input")
    if isinstance(tool_input, dict):
        candidates.extend(
            [
                tool_input.get("prompt"),
                tool_input.get("description"),
                tool_input.get("message"),
            ]
        )
    for candidate in candidates:
        text = _string(candidate)
        if text:
            return _truncate(text)
    return ""


def _extract_session_id(input_data: dict[str, Any]) -> str:
    return _first_string(
        input_data.get("session_id"),
        input_data.get("sessionId"),
        input_data.get("conversation_id"),
        input_data.get("conversationId"),
        input_data.get("thread_id"),
        input_data.get("threadId"),
        input_data.get("run_id"),
        input_data.get("runId"),
        _extract_env_session_id(_detect_platform(input_data)),
    )


def _extract_env_session_id(platform: str | None = None) -> str:
    preferred = _string(platform)
    for candidate_platform, env_names in ENV_SESSION_KEYS:
        if preferred and candidate_platform != preferred:
            continue
        value = _first_string(*(os.environ.get(env_name) for env_name in env_names))
        if value:
            return value
    if preferred:
        return ""
    for _candidate_platform, env_names in ENV_SESSION_KEYS:
        value = _first_string(*(os.environ.get(env_name) for env_name in env_names))
        if value:
            return value
    return ""


def _resolve_active_task_id(root: Path, input_data: dict[str, Any]) -> str:
    try:
        scripts_dir = root / ".trellis" / "scripts"
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        from common.active_task import resolve_active_task  # type: ignore[import-not-found]

        active = resolve_active_task(
            root, input_data, platform=_detect_platform(input_data)
        )
    except Exception:
        return ""

    task_path = _string(getattr(active, "task_path", ""))
    if not task_path:
        return ""
    return Path(task_path).name


def _derive_lifecycle(
    kind: str, hook_event_name: str, tool_kind: str | None = None
) -> tuple[str, str]:
    lowered = hook_event_name.lower()
    if kind == "session_end" or lowered in {"sessionend", "session_end", "stop"}:
        return "session_end", "end"
    if kind == "session":
        return "session_start", "start"
    if kind == "prompt":
        return "prompt_submit", "observe"

    phase = "observe"
    if lowered.startswith("pre") or lowered.startswith("before"):
        phase = "start"
    elif lowered.startswith("post") or lowered.startswith("after"):
        phase = "end"

    base = "tool"
    if tool_kind == "skill":
        base = "skill"
    elif tool_kind == "mcp":
        base = "mcp"
    elif kind == "agent_spawn":
        base = "agent"
    return f"{base}_{phase}", phase


def _classify_tool(tool_name: str) -> tuple[str, dict[str, str]]:
    if tool_name.startswith("mcp__"):
        parts = tool_name.split("__", 2)
        if len(parts) == 3:
            return "mcp", {"mcp_server": parts[1], "mcp_tool": parts[2]}
        return "mcp", {}
    lowered = tool_name.lower()
    if lowered in {"task", "agent", "subagent"}:
        return "subagent", {}
    if "skill" in lowered:
        return "skill", {}
    if lowered in {"bash", "shell", "shell_command", "execute"}:
        return "shell", {}
    return "tool", {}


def _extract_tool_event(input_data: dict[str, Any]) -> dict[str, Any]:
    tool_name = _first_string(
        input_data.get("tool_name"),
        input_data.get("toolName"),
        input_data.get("agent_name"),
    )
    tool_input = input_data.get("tool_input")
    if not tool_name and isinstance(tool_input, dict):
        tool_name = _first_string(
            tool_input.get("tool"),
            tool_input.get("name"),
            tool_input.get("subagent_type"),
            tool_input.get("subagentType"),
            tool_input.get("subagent_type_name"),
            tool_input.get("subagentTypeName"),
        )
    tool_kind, extras = _classify_tool(tool_name)
    payload: dict[str, Any] = {
        "tool_name": tool_name,
        "tool_kind": tool_kind,
        "type": tool_kind,
    }
    payload.update(extras)

    if isinstance(tool_input, dict):
        payload["tool_input_keys"] = sorted(
            key for key in tool_input.keys() if isinstance(key, str)
        )[:12]
        tool_description = _first_string(
            tool_input.get("description"),
            tool_input.get("meta"),
            input_data.get("description"),
            input_data.get("meta"),
        )
        if tool_description:
            payload["tool_description"] = tool_description
        prompt_preview = _extract_prompt_preview({"tool_input": tool_input})
        if prompt_preview:
            payload["tool_input_preview"] = prompt_preview
        skill_name = _first_string(
            tool_input.get("skill_name"),
            tool_input.get("skillName"),
            tool_input.get("selected_skill"),
            tool_input.get("selectedSkill"),
        )
        if skill_name:
            payload["skill_name"] = skill_name
    else:
        prompt_preview = _extract_prompt_preview(input_data)
        if prompt_preview:
            payload["tool_input_preview"] = prompt_preview

    explicit_skill = _first_string(
        input_data.get("skill_name"),
        input_data.get("skillName"),
        input_data.get("selected_skill"),
        input_data.get("selectedSkill"),
    )
    if explicit_skill:
        payload["skill_name"] = explicit_skill
        payload["tool_kind"] = "skill"
        payload["type"] = "skill"

    return payload


def _build_record(
    kind: str, input_data: dict[str, Any], root: Path
) -> dict[str, Any]:
    hook_event = _first_string(
        input_data.get("hook_event_name"),
        input_data.get("hookEventName"),
        input_data.get("event"),
    )
    record: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "trellis-hook",
        "event_kind": kind,
        "platform": _detect_platform(input_data),
        "cwd": _string(input_data.get("cwd")) or str(root),
    }

    session_id = _extract_session_id(input_data)
    if session_id:
        record["session_id"] = session_id
    active_task_id = _first_string(
        input_data.get("active_task_id"),
        input_data.get("activeTaskId"),
        _resolve_active_task_id(root, input_data),
    )
    if active_task_id:
        record["active_task_id"] = active_task_id

    if kind == "prompt":
        preview = _extract_prompt_preview(input_data)
        if preview:
            record["prompt_preview"] = preview
    elif kind in {"tool", "agent_spawn"}:
        record.update(_extract_tool_event(input_data))
        record["target"] = _first_string(
            record.get("skill_name"), record.get("tool_name")
        )

    action, phase = _derive_lifecycle(
        kind, hook_event, _string(record.get("tool_kind"))
    )
    record["action"] = action
    record["phase"] = phase

    if hook_event:
        record["hook_event_name"] = hook_event

    matcher = _first_string(input_data.get("matcher"))
    if matcher:
        record["matcher"] = matcher

    return record


def _normalize_record(record: dict[str, Any]) -> dict[str, Any] | None:
    event_kind = _string(record.get("event_kind"))
    tool_kind = _string(record.get("tool_kind"))

    if event_kind in {"tool", "agent_spawn"}:
        if tool_kind == "mcp":
            record["action"] = "mcp_call"
            record["report_kind"] = "mcp_call"
        elif tool_kind == "skill":
            record["action"] = "skill_call"
            record["report_kind"] = "skill_call"
        else:
            record["report_kind"] = "tool_call"

    return record


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _load_call_state(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _save_call_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")


def _build_call_state_key(record: dict[str, Any]) -> str:
    return "::".join(
        [
            _first_string(record.get("platform"), "unknown"),
            _first_string(record.get("session_id"), "no-session"),
            _first_string(record.get("tool_kind"), "tool"),
            _first_string(record.get("skill_name"), record.get("tool_name"), "unknown"),
        ]
    )


def _track_call_timing(root: Path, record: dict[str, Any]) -> dict[str, Any] | None:
    event_kind = _string(record.get("event_kind"))
    phase = _string(record.get("phase"))
    if event_kind not in {"tool", "agent_spawn"}:
        return record

    state_path = root / DEFAULT_CALL_STATE_PATH
    state = _load_call_state(state_path)
    call_key = _build_call_state_key(record)
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    if phase == "start":
        state[call_key] = {
            "started_at_ms": now_ms,
            "tool_name": _string(record.get("tool_name")),
            "skill_name": _string(record.get("skill_name")),
        }
        _save_call_state(state_path, state)
        return None

    if phase == "end":
        started = state.pop(call_key, None)
        _save_call_state(state_path, state)
        if isinstance(started, dict):
            started_at_ms = started.get("started_at_ms")
            if isinstance(started_at_ms, int):
                record["duration_ms"] = max(now_ms - started_at_ms, 0)
        if "duration_ms" not in record:
            record["duration_ms"] = 0

    return record


def _load_remote_config(root: Path) -> dict[str, Any]:
    config_path = root / DEFAULT_REMOTE_CONFIG_PATH
    try:
        raw = config_path.read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _extract_frontmatter_description(skill_file: Path) -> str:
    try:
        raw = skill_file.read_text(encoding="utf-8")
    except OSError:
        return ""
    lines = raw.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    for line in lines[1:40]:
        stripped = line.strip()
        if stripped == "---":
            break
        if not stripped.startswith("description:"):
            continue
        _, _, value = stripped.partition(":")
        return value.strip().strip('"').strip("'")
    return ""


def _find_skill_file(root: Path, skill_name: str) -> Path | None:
    candidates = [
        root / ".agents" / "skills" / skill_name / "SKILL.md",
        root / ".trellis" / "skills" / skill_name / "SKILL.md",
        Path.home() / ".agents" / "skills" / skill_name / "SKILL.md",
        Path.home() / ".codex" / "skills" / skill_name / "SKILL.md",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _derive_skill_description(record: dict[str, Any]) -> str:
    skill_name = _string(record.get("skill_name"))
    if not skill_name:
        return ""
    cwd = Path(_string(record.get("cwd")) or os.getcwd())
    root = _find_trellis_root(cwd) or cwd
    skill_file = _find_skill_file(root, skill_name)
    if skill_file is None:
        return ""
    return _extract_frontmatter_description(skill_file)


def _remote_reporting_enabled(config: dict[str, Any]) -> bool:
    if config.get("enabled") is False:
        return False
    return bool(_string(config.get("token")))


def _remote_debug_enabled(config: dict[str, Any]) -> bool:
    return bool(config.get("debug"))


def _should_report_remote(record: dict[str, Any], config: dict[str, Any]) -> bool:
    if not _remote_reporting_enabled(config):
        return False
    return _string(record.get("report_kind")) in {"skill_call", "mcp_call"}


def _build_remote_headers(config: dict[str, Any]) -> dict[str, str]:
    headers = {"Content-Type": "application/json; charset=utf-8"}
    token = _string(config.get("token"))
    if token:
        token_header = _string(config.get("tokenHeader")) or DEFAULT_REMOTE_TOKEN_HEADER
        headers[token_header] = token

    extra_headers = config.get("headers")
    if isinstance(extra_headers, dict):
        for key, value in extra_headers.items():
            if isinstance(key, str) and isinstance(value, str):
                headers[key] = value
    return headers


def _build_remote_url(base_url: str, path: str, params: dict[str, Any] | None = None) -> str:
    url = f"{base_url.rstrip('/')}{path}"
    if params:
        query = urllib.parse.urlencode(
            {
                key: value
                for key, value in params.items()
                if isinstance(key, str) and value is not None
            }
        )
        if query:
            url = f"{url}?{query}"
    return url


def _remote_request(
    base_url: str,
    path: str,
    headers: dict[str, str],
    timeout_sec: float,
    *,
    method: str = "GET",
    data: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> Any | None:
    payload = (
        json.dumps(data, ensure_ascii=False).encode("utf-8")
        if data is not None and method.upper() != "GET"
        else None
    )
    request = urllib.request.Request(
        _build_remote_url(base_url, path, params),
        data=payload,
        headers=headers,
        method=method.upper(),
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None

    if isinstance(parsed, dict):
        if parsed.get("c") == 0:
            return parsed.get("d")
        if parsed.get("code") == 0:
            return parsed.get("data")
    return None


def _derive_remote_domain(record: dict[str, Any], config: dict[str, Any]) -> str:
    configured = _string(config.get("domain"))
    if configured:
        return configured
    report_kind = _string(record.get("report_kind")) or _string(record.get("action"))
    if report_kind == "mcp_call":
        return "mcp"
    if report_kind == "skill_call":
        return "skill"
    return DEFAULT_REMOTE_DOMAIN


def _derive_remote_scenario(record: dict[str, Any], config: dict[str, Any]) -> str:
    configured = _string(config.get("scenario"))
    if configured:
        return configured
    skill_description = _derive_skill_description(record)
    if skill_description:
        return skill_description
    human_description = _first_string(
        record.get("tool_description"),
        record.get("skill_description"),
    )
    if human_description:
        return human_description
    target = _string(record.get("target"))
    if target:
        return target
    platform = _string(record.get("platform")) or "unknown"
    report_kind = _string(record.get("report_kind")) or _string(record.get("action"))
    if report_kind == "mcp_call":
        return f"{platform}:mcp"
    if report_kind == "skill_call":
        return f"{platform}:skill"
    return f"{platform}:tool"


def _derive_remote_metric(record: dict[str, Any], config: dict[str, Any]) -> str:
    configured = _string(config.get("metric"))
    if configured:
        return configured
    return _first_string(
        record.get("target"),
        record.get("skill_name"),
        record.get("tool_name"),
        record.get("report_kind"),
        "unknown",
    )


def _derive_remote_tool_name(record: dict[str, Any]) -> str:
    tool_kind = _string(record.get("tool_kind"))
    if tool_kind == "mcp":
        return f"mcp::{_string(record.get('mcp_tool')) or _string(record.get('target'))}"
    if tool_kind == "skill":
        return f"skill::{_string(record.get('skill_name')) or _string(record.get('target'))}"
    return _string(record.get("target")) or _string(record.get("tool_name"))


def _read_git_user_name(cwd: str) -> str:
    try:
        result = subprocess.run(
            ["git", "config", "user.name"],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=2,
            check=False,
        )
    except Exception:
        return ""
    if result.returncode != 0:
        return ""
    return _string(result.stdout)


def _derive_reporter_identity(record: dict[str, Any], config: dict[str, Any]) -> str:
    configured_user = _string(config.get("userId"))
    if configured_user:
        return configured_user
    configured_operator = _string(config.get("operator"))
    if configured_operator:
        return configured_operator
    cwd = _string(record.get("cwd")) or os.getcwd()
    git_user = _read_git_user_name(cwd)
    if git_user:
        return git_user
    return DEFAULT_REMOTE_USER_ID


def _build_remote_description(record: dict[str, Any]) -> str:
    report_kind = _string(record.get("report_kind"))
    target = _first_string(record.get("target"), record.get("tool_name"), "unknown")
    if report_kind == "mcp_call":
        server = _string(record.get("mcp_server"))
        tool = _string(record.get("mcp_tool"))
        detail = "/".join(part for part in (server, tool) if part)
        return f"MCP call: {detail or target}"
    if report_kind == "skill_call":
        return f"Skill call: {target}"
    return f"Tool call: {target}"


def _build_log_payload(record: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    target = _string(record.get("target")) or _string(record.get("tool_name"))
    domain = _derive_remote_domain(record, config)
    scenario = _derive_remote_scenario(record, config)
    metric = _derive_remote_metric(record, config)
    remote_tool_name = _derive_remote_tool_name(record)
    reporter_identity = _derive_reporter_identity(record, config)
    description = _build_remote_description(record)
    timestamp_raw = _string(record.get("timestamp"))
    try:
        timestamp_ms = int(
            datetime.fromisoformat(timestamp_raw.replace("Z", "+00:00")).timestamp()
            * 1000
        )
    except ValueError:
        timestamp_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    duration_ms = max(int(record.get("duration_ms") or 0), 0)

    remark = {
        "platform": _string(record.get("platform")),
        "sessionId": _string(record.get("session_id")),
        "toolName": _string(record.get("tool_name")),
        "skillName": _string(record.get("skill_name")),
        "mcpServer": _string(record.get("mcp_server")),
        "mcpTool": _string(record.get("mcp_tool")),
        "target": target,
        "reportKind": _string(record.get("report_kind")),
    }
    return {
        "domain": domain,
        "scenario": scenario,
        "metric": metric,
        "subDomain": scenario,
        "metricName": metric,
        "metricType": _string(config.get("metricType")) or DEFAULT_REMOTE_METRIC_TYPE,
        "scenarioType": _string(config.get("scenarioType"))
        or DEFAULT_REMOTE_SCENARIO_TYPE,
        "toolName": remote_tool_name,
        "baselineValue": 300,
        "targetValueH1": 0,
        "targetValueH2": 0,
        "role": _string(config.get("role")) or DEFAULT_REMOTE_ROLE,
        "description": description,
        "originalTotalDuration": 300,
        "singleScenarioTotalCost": 0,
        "userId": reporter_identity,
        "toolCallCount": 1,
        "toolSingleDuration": duration_ms,
        "toolCallTime": timestamp_ms,
        "operator": reporter_identity,
        "remark": json.dumps(remark, ensure_ascii=False),
        "aiCodeAdoptionRate": 1,
        "calculatedValue": 0,
        "createTime": timestamp_ms,
        "rawValue": 300,
        "recordTime": timestamp_ms,
    }

def _post_remote_report(record: dict[str, Any], config: dict[str, Any]) -> None:
    if not _remote_reporting_enabled(config):
        return

    timeout_raw = _string(config.get("timeoutMs"))
    try:
        timeout_ms = int(timeout_raw) if timeout_raw else DEFAULT_REMOTE_TIMEOUT_MS
    except ValueError:
        timeout_ms = DEFAULT_REMOTE_TIMEOUT_MS
    timeout_sec = max(timeout_ms, 100) / 1000.0
    headers = _build_remote_headers(config)
    base_url = _string(config.get("baseUrl")) or DEFAULT_REMOTE_BASE_URL
    payload = _build_log_payload(record, config)
    result = _remote_request(
        base_url,
        DEFAULT_REMOTE_REPORT_PATH,
        headers,
        timeout_sec,
        method="POST",
        data=payload,
    )

    if _remote_debug_enabled(config):
        debug_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "target": _string(record.get("target")),
            "report_kind": _string(record.get("report_kind")),
            "url": _build_remote_url(base_url, DEFAULT_REMOTE_REPORT_PATH),
            "request": {
                "domain": payload.get("domain"),
                "subDomain": payload.get("subDomain"),
                "scenario": payload.get("scenario"),
                "metric": payload.get("metric"),
                "toolName": payload.get("toolName"),
                "userId": payload.get("userId"),
                "operator": payload.get("operator"),
            },
            "success": result is not None,
            "response": result,
        }
        _append_jsonl(
            Path(_string(config.get("debugFile")) or ".trellis/.runtime/telemetry/remote-debug.jsonl"),
            debug_record,
        )


def _session_share_config(config: dict[str, Any]) -> dict[str, Any]:
    raw = config.get("sessionShare")
    return raw if isinstance(raw, dict) else {}


def _session_share_enabled(config: dict[str, Any]) -> bool:
    env_value = os.environ.get("TRELLIS_SESSION_SHARE")
    if env_value is not None:
        return env_value.strip().lower() in {"1", "true", "yes", "on"}
    share_config = _session_share_config(config)
    return share_config.get("enabled") is True


def _session_share_timeout_sec(config: dict[str, Any]) -> float:
    share_config = _session_share_config(config)
    timeout_raw = _string(share_config.get("timeoutMs"))
    try:
        timeout_ms = int(timeout_raw) if timeout_raw else DEFAULT_SESSION_SHARE_TIMEOUT_MS
    except ValueError:
        timeout_ms = DEFAULT_SESSION_SHARE_TIMEOUT_MS
    return max(timeout_ms, 1000) / 1000.0


def _session_share_command(config: dict[str, Any], session_id: str) -> list[str]:
    share_config = _session_share_config(config)
    command = _string(share_config.get("moonCommand")) or DEFAULT_SESSION_SHARE_COMMAND
    args_raw = share_config.get("moonArgs")
    args = (
        [part for part in args_raw if isinstance(part, str) and part]
        if isinstance(args_raw, list)
        else list(DEFAULT_SESSION_SHARE_ARGS)
    )
    return [command, *args, session_id]


def _extract_share_url(output: str) -> str:
    match = re.search(r"https?://\S+", output)
    return match.group(0).rstrip(".,;") if match else ""


def _session_share_status_base(
    record: dict[str, Any],
    status: str,
    reason: str = "",
) -> dict[str, Any]:
    result = {
        "schemaVersion": 1,
        "event": "session_end",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "platform": _string(record.get("platform")),
        "sessionId": _string(record.get("session_id")),
        "activeTaskId": _string(record.get("active_task_id")),
        "endedAt": _string(record.get("timestamp")),
        "reportStatus": status,
    }
    if reason:
        result["reason"] = reason
    return result


def _run_session_share(
    root: Path, record: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any] | None:
    if not _session_share_enabled(config):
        return None

    session_id = _string(record.get("session_id"))
    if not session_id:
        return _session_share_status_base(record, "skipped", "missing_session_id")

    command = _session_share_command(config, session_id)
    executable = command[0]
    resolved = executable if os.path.sep in executable else shutil.which(executable)
    if not resolved:
        status = _session_share_status_base(record, "skipped", "moon_not_found")
        status["moonCommand"] = command
        return status

    run_command = [resolved, *command[1:]]
    status = _session_share_status_base(record, "attempted")
    status["moonCommand"] = command
    try:
        completed = subprocess.run(
            run_command,
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_session_share_timeout_sec(config),
            check=False,
        )
    except subprocess.TimeoutExpired:
        status["reportStatus"] = "failed"
        status["reason"] = "timeout"
        return status
    except Exception as exc:
        status["reportStatus"] = "failed"
        status["reason"] = _truncate(type(exc).__name__, 80)
        return status

    output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
    status["moonExitCode"] = completed.returncode
    share_url = _extract_share_url(output)
    if share_url:
        status["shareUrl"] = share_url
    if completed.returncode == 0:
        status["reportStatus"] = "succeeded"
    else:
        status["reportStatus"] = "failed"
        status["errorSummary"] = _truncate(output, 240)
    return status


def _session_share_notify_user(config: dict[str, Any]) -> bool:
    share_config = _session_share_config(config)
    raw = share_config.get("notifyUser")
    return raw is not False


def _session_share_write_journal(config: dict[str, Any]) -> bool:
    share_config = _session_share_config(config)
    raw = share_config.get("writeJournal")
    return raw is not False


def _format_session_share_notification(status: dict[str, Any]) -> str:
    report_status = _string(status.get("reportStatus"))
    if report_status == "succeeded":
        share_url = _string(status.get("shareUrl"))
        if share_url:
            return f"Trellis session uploaded to Moon: {share_url}"
        return "Trellis session uploaded to Moon."
    if report_status == "failed":
        reason = _string(status.get("reason")) or _string(status.get("errorSummary"))
        suffix = f": {reason}" if reason else ""
        return f"Trellis session upload to Moon failed{suffix}"
    if report_status == "skipped" and _string(status.get("reason")) != "disabled":
        reason = _string(status.get("reason"))
        suffix = f": {reason}" if reason else ""
        return f"Trellis session upload to Moon skipped{suffix}"
    return ""


def _append_text_once(path: Path, text: str, marker: str) -> None:
    try:
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        if marker and marker in existing:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            if existing and not existing.endswith("\n"):
                handle.write("\n")
            handle.write(text)
            if not text.endswith("\n"):
                handle.write("\n")
    except Exception:
        return


def _active_journal_file(root: Path) -> Path | None:
    try:
        scripts_dir = root / ".trellis" / "scripts"
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        from common.paths import get_active_journal_file  # type: ignore[import-not-found]

        journal = get_active_journal_file(root)
        return journal if isinstance(journal, Path) else None
    except Exception:
        return None


def _task_session_share_file(root: Path, active_task_id: str) -> Path | None:
    task_id = _string(active_task_id).strip()
    if not task_id or "/" in task_id or "\\" in task_id or task_id in {".", ".."}:
        return None
    task_dir = root / ".trellis" / "tasks" / task_id
    if not task_dir.is_dir():
        return None
    return task_dir / "session-share.md"


def _format_session_share_markdown(status: dict[str, Any]) -> str:
    session_id = _string(status.get("sessionId"))
    timestamp = _string(status.get("timestamp"))
    report_status = _string(status.get("reportStatus"))
    share_url = _string(status.get("shareUrl"))
    reason = _string(status.get("reason")) or _string(status.get("errorSummary"))

    lines = [
        "",
        "### Moon Session Upload",
        "",
        f"- Time: {timestamp or datetime.now(timezone.utc).isoformat()}",
        f"- Session: `{session_id}`",
        f"- Status: `{report_status}`",
    ]
    if share_url:
        lines.append(f"- Moon link: {share_url}")
    if reason:
        lines.append(f"- Reason: `{reason}`")
    lines.append("")
    return "\n".join(lines)


def _record_session_share_to_markdown(root: Path, status: dict[str, Any]) -> None:
    marker = _string(status.get("shareUrl"))
    if not marker:
        marker = "::".join(
            part
            for part in (
                _string(status.get("sessionId")),
                _string(status.get("reportStatus")),
                _string(status.get("reason")) or _string(status.get("errorSummary")),
            )
            if part
        )
    if not marker:
        return
    markdown = _format_session_share_markdown(status)

    journal = _active_journal_file(root)
    if journal is not None:
        _append_text_once(journal, markdown, marker)

    task_file = _task_session_share_file(root, _string(status.get("activeTaskId")))
    if task_file is not None:
        if not task_file.exists():
            _append_text_once(
                task_file,
                "# Session Share\n\nMoon session upload records for this task.\n",
                "",
            )
        _append_text_once(task_file, markdown, marker)


def _maybe_record_session_share(
    root: Path, record: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any] | None:
    if _string(record.get("action")) != "session_end":
        return None
    status = _run_session_share(root, record, config)
    if status is None:
        return None
    path = root / DEFAULT_SESSION_SHARE_STATUS_PATH
    _append_jsonl(path, status)
    if _session_share_write_journal(config):
        _record_session_share_to_markdown(root, status)
    return status


def _read_latest_jsonl(path: Path) -> dict[str, Any] | None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    return None


def _find_latest_session_record(root: Path) -> dict[str, Any] | None:
    path = root / ".trellis" / ".runtime" / "telemetry" / "hook-events.jsonl"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            record = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue
        if _string(record.get("session_id")):
            return record
    return None


def _find_existing_session_share(root: Path, session_id: str) -> dict[str, Any] | None:
    path = root / DEFAULT_SESSION_SHARE_STATUS_PATH
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            status = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if not isinstance(status, dict):
            continue
        if _string(status.get("sessionId")) != session_id:
            continue
        if _string(status.get("reportStatus")) == "succeeded" and _string(status.get("shareUrl")):
            return status
    return None


def _share_latest_session(root: Path, config: dict[str, Any]) -> dict[str, Any] | None:
    if not _session_share_enabled(config):
        return None

    latest = _find_latest_session_record(root)
    if latest is None:
        latest = _read_latest_jsonl(
            root / ".trellis" / ".runtime" / "telemetry" / "hook-events.jsonl"
        ) or {}

    session_id = _string(latest.get("session_id"))
    if not session_id:
        env_session_id = _extract_env_session_id(_string(latest.get("platform")) or None)
        if env_session_id:
            latest = {
                **latest,
                "platform": _string(latest.get("platform")) or _detect_platform({}),
                "cwd": _string(latest.get("cwd")) or str(root),
                "session_id": env_session_id,
            }
            session_id = env_session_id
    if not session_id:
        status = _session_share_status_base(latest, "skipped", "missing_session_id")
        status["event"] = "session_end"
        status["timestamp"] = datetime.now(timezone.utc).isoformat()
        return status

    existing = _find_existing_session_share(root, session_id)
    if existing is not None:
        existing["reused"] = True
        return existing

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "trellis-manual-finish-work",
        "event_kind": "session_end",
        "platform": _string(latest.get("platform")) or None,
        "cwd": _string(latest.get("cwd")) or str(root),
        "session_id": session_id,
        "action": "session_end",
        "phase": "end",
    }
    active_task_id = _string(latest.get("active_task_id"))
    if active_task_id:
        record["active_task_id"] = active_task_id

    try:
        _append_jsonl(
            root / ".trellis" / ".runtime" / "telemetry" / "hook-events.jsonl",
            record,
        )
    except Exception:
        pass

    status = _run_session_share(root, record, config)
    if status is None:
        return None
    _append_jsonl(root / DEFAULT_SESSION_SHARE_STATUS_PATH, status)
    if _session_share_write_journal(config):
        _record_session_share_to_markdown(root, status)
    return status


def main() -> int:
    if os.environ.get("TRELLIS_HOOKS") == "0" or os.environ.get(
        "TRELLIS_DISABLE_HOOKS"
    ) == "1":
        return 0

    event_kind = sys.argv[1] if len(sys.argv) > 1 else "unknown"

    try:
        input_data = json.load(sys.stdin)
    except Exception:
        input_data = {}

    cwd_str = _string(input_data.get("cwd")) or os.getcwd()
    root = _find_trellis_root(Path(cwd_str))
    if root is None:
        return 0
    remote_config = _load_remote_config(root)

    if event_kind in {"share_latest_session", "share-latest-session"}:
        try:
            status = _share_latest_session(root, remote_config)
            if status is None:
                return 0
            notification = _format_session_share_notification(status)
            if notification:
                print(notification)
        except Exception:
            return 0
        return 0

    telemetry_path = (
        root / ".trellis" / ".runtime" / "telemetry" / "hook-events.jsonl"
    )
    record = _track_call_timing(root, _build_record(event_kind, input_data, root))
    if record is None:
        return 0
    record = _normalize_record(record)
    if record is None:
        return 0
    try:
        _append_jsonl(telemetry_path, record)
    except Exception:
        return 0
    try:
        if _should_report_remote(record, remote_config):
            _post_remote_report(record, remote_config)
        share_status = _maybe_record_session_share(root, record, remote_config)
        if share_status is not None and _session_share_notify_user(remote_config):
            notification = _format_session_share_notification(share_status)
            if notification:
                print(notification)
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
