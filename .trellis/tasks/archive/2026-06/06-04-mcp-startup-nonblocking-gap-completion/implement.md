# MCP startup nonblocking gap completion implementation plan

## Preconditions

- Read `prd.md` and `design.md`.
- Run `trellis-before-dev` before editing code.
- Record pre-dev gate with:

```bash
python3 ./.trellis/scripts/task.py gate pre-dev .trellis/tasks/06-04-mcp-startup-nonblocking-gap-completion --spec .trellis/spec/guides/index.md --spec .trellis/spec/guides/cross-layer-thinking-guide.md --spec .trellis/spec/guides/code-reuse-thinking-guide.md
```

## Step 1: Add nonblocking MCP manager primitives

Files:

- `codex-rs/codex-mcp/src/rmcp_client.rs`
- `codex-rs/codex-mcp/src/connection_manager.rs`
- `codex-rs/codex-mcp/src/connection_manager_tests.rs`

Tasks:

- Add an `AsyncManagedClient` helper that returns ready/failed/pending without awaiting startup.
- Add `McpConnectionManager::tool_info_if_available(server, tool)`.
- Add available resource/template APIs that skip pending optional servers.
- Add specified-server resource/template/read APIs that return still-starting instead of awaiting pending startup.
- Add unit tests proving pending clients are skipped and blocking APIs remain intentionally blocking.

Quality checks:

```bash
just test -p codex-mcp
```

## Step 2: Replace blocking metadata lookup

Files:

- `codex-rs/core/src/mcp_tool_call.rs`
- `codex-rs/core/src/mcp_tool_call_tests.rs`

Tasks:

- Replace `lookup_mcp_tool_metadata()` full `list_all_tools().await` with target `tool_info_if_available`.
- Replace `lookup_mcp_app_usage_metadata()` full `list_all_tools().await`.
- Ensure connector metadata fallback uses cached/available connector data only.
- Add regression tests with ready target server plus unrelated pending optional server.

Acceptance covered:

- MCP approval metadata no longer waits on unrelated pending MCP.
- MCP app usage metadata no longer waits on unrelated pending MCP.

## Step 3: Replace connector and plugin-install blocking paths

Files:

- `codex-rs/core/src/connectors.rs`
- `codex-rs/core/src/connectors_tests.rs`
- `codex-rs/core/src/tools/handlers/request_plugin_install.rs`
- `codex-rs/core/src/tools/handlers/request_plugin_install_tests.rs`

Tasks:

- Change default connector discovery to `list_available_tools()`.
- Keep `force_refetch` bounded and Codex Apps-specific.
- Change plugin install request discovery to available tools.
- Change missing connector refresh to start from available tools and only hard-refresh Codex Apps when relevant.
- Add regression tests for unrelated pending MCP not blocking connector/plugin discovery.

Acceptance covered:

- connector discovery default no longer uses blocking `list_all_tools().await`.
- plugin install / missing connector refresh default no longer uses blocking `list_all_tools().await`.

## Step 4: Make MCP resource tools nonblocking

Files:

- `codex-rs/core/src/tools/spec_plan.rs`
- `codex-rs/core/src/tools/spec_plan_tests.rs`
- `codex-rs/core/src/tools/handlers/mcp_resource/list_mcp_resources.rs`
- `codex-rs/core/src/tools/handlers/mcp_resource/list_mcp_resource_templates.rs`
- `codex-rs/core/src/tools/handlers/mcp_resource/read_mcp_resource.rs`
- `codex-rs/core/src/tools/handlers/mcp_resource_tests.rs`
- `codex-rs/core/src/session/mcp.rs`

Tasks:

- Prefer keeping resource tools exposed, but make handlers nonblocking.
- All-server list skips pending optional servers.
- Specified pending server returns a clear still-starting message.
- Failed server returns startup failure message.
- Add tests for list resources/templates and read resource pending behavior.

Acceptance covered:

- resource tools do not block on pending optional servers.
- specified pending target produces understandable unavailable state.

## Step 5: Add session / turn / subagent regression tests

Files likely:

- `codex-rs/core/tests/suite/search_tool.rs` or a new suite file near MCP/tool tests.
- `codex-rs/core/src/tools/handlers/multi_agents_tests.rs` if lower-level spawn harness is easier.

Tasks:

- Parent turn first request:
  - configure ready MCP and slow optional MCP.
  - assert first request sees ready/snapshot tools only.
- Later turn:
  - unblock/let slow MCP become ready.
  - assert later request includes delayed tool.
- Spawned subagent:
  - parent spawns child while slow optional MCP pending.
  - assert spawn/child first model request proceeds without waiting for slow optional MCP.
  - assert child first request omits pending optional tool.
- Required behavior:
  - required MCP failure still blocks/fails as before.

Notes:

- Reuse existing `stdio_server_bin()` and response mock helpers where possible.
- If a custom slow MCP fixture is needed, prefer adding behavior to existing test MCP server over ad hoc sleeps in production code.

## Step 6: Validation

Always run:

```bash
cd codex-rs
just fmt
```

Run targeted tests:

```bash
cd codex-rs
just test -p codex-mcp
just test -p codex-core
```

If `just test -p codex-core` is blocked by existing unrelated `ModelClient::stream` signature mismatches, record the exact compiler errors and run the narrowest affected test targets possible once compile is restored. Do not claim full core validation passed.

Before final response:

```bash
git diff --stat
git status --short
```

## Review Checklist

- No ThreadSpawn-specific required MCP bypass.
- No new broad `list_all_tools().await` in turn-time or tool-execution metadata paths.
- Blocking APIs are still available for intentional waits.
- Optional pending MCP is skipped or reported as still-starting.
- Required MCP behavior has regression coverage.
- Tests prove both main-session and spawned-subagent paths.
