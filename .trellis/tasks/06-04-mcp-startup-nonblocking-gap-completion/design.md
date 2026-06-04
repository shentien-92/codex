# MCP startup nonblocking gap completion design

## Scope

本设计补齐旧 PRD 已验收出的 MCP nonblocking 缺口。目标是让 optional MCP server pending 时，不再通过 metadata、resource、connector、plugin-install、spawned subagent turn 等路径重新阻塞主会话或子会话。

不重做 TUI slash-command gating 与 resume hardening，除非实现或测试发现它们仍直接影响本任务。

## Current Problem Shape

### 已经做对的路径

- `codex-rs/core/src/session/turn.rs::built_tools()` 使用 `McpConnectionManager::list_available_tools()`。
- `list_available_tools()` 只返回 ready 或 startup snapshot-backed tools。
- pending optional server 无 snapshot 时会从当前 model-visible tools 省略。

### 仍会阻塞的路径

- `codex-rs/core/src/mcp_tool_call.rs`
  - `lookup_mcp_tool_metadata()` 调 `list_all_tools().await`。
  - `lookup_mcp_app_usage_metadata()` 调 `list_all_tools().await`。
- `codex-rs/core/src/connectors.rs`
  - connector discovery 默认分支调 `list_all_tools().await`。
  - 空 tools 时针对 Codex Apps 的 bounded wait 可以保留，但前置全量等待必须移除。
- `codex-rs/core/src/tools/handlers/request_plugin_install.rs`
  - plugin install request 与 missing connector refresh 调 `list_all_tools().await`。
- `codex-rs/core/src/tools/spec_plan.rs` 与 `mcp_resource/*`
  - `has_mcp_servers` 导致 `Some(empty)` 时仍暴露 MCP resource tools。
  - all-resource handlers 调 `list_all_resources/templates().await`，会 await pending clients。

## Design Principles

- **Manager owns readiness knowledge**：MCP startup 状态判断集中在 `codex-mcp` 的 `McpConnectionManager` / `AsyncManagedClient`，调用侧不复制 `now_or_never` 或 startup flag 逻辑。
- **Blocking APIs stay explicit**：保留 `list_all_tools().await`、`list_all_resources().await` 等 blocking API，但只用于确实需要等待的管理或 required startup 场景。
- **Turn-time paths use available APIs**：模型 turn、tool execution metadata、connector/plugin metadata、resource listing 默认使用 nonblocking available APIs。
- **Required stays strict**：不新增 ThreadSpawn-specific required MCP bypass，不把 required server 降级为 optional。
- **Unavailable is explicit**：如果请求的目标 server/resource/tool 仍在启动，返回清晰的 still-starting/unavailable 信息，而不是泛化 timeout 或被无关 pending server 卡住。

## Proposed API Changes

### `codex-mcp/src/rmcp_client.rs`

Add nonblocking readiness helpers on `AsyncManagedClient`:

- `fn client_if_available(&self) -> Option<Result<ManagedClient, StartupOutcomeError>>`
  - Uses the shared future's `now_or_never()`.
  - Returns `None` if startup is still pending.
  - Returns `Some(Ok(client))` if ready.
  - Returns `Some(Err(error))` if startup completed with failure.
- Keep `listed_tools_if_available()` as the tool-specific version.

This keeps future polling mechanics internal to `AsyncManagedClient`.

### `codex-mcp/src/connection_manager.rs`

Add available APIs:

- `fn tool_info_if_available(&self, server: &str, tool: &str) -> Option<ToolInfo>`
  - Searches `list_available_tools()`.
  - Does not wait for unrelated servers.

- `fn list_available_resources(&self) -> HashMap<String, Vec<Resource>>`
  - Iterates clients.
  - Skips pending clients.
  - For ready clients, list resources with existing per-client timeout.
  - Because resource listing itself is async RPC, this should be `async fn`, but it must not await startup of pending clients.
  - Name can be `list_available_resources` even though per-ready-server resource RPC is awaited.

- `async fn list_available_resource_templates(&self) -> HashMap<String, Vec<ResourceTemplate>>`
  - Same as resources/templates.

- `async fn list_resources_if_ready(...) -> Result<ListResourcesResult, McpServerReadinessError>`
- `async fn list_resource_templates_if_ready(...) -> Result<ListResourceTemplatesResult, McpServerReadinessError>`
- `async fn read_resource_if_ready(...) -> Result<ReadResourceResult, McpServerReadinessError>`
  - Only waits on target server if it is already ready.
  - Pending optional target returns `StillStarting`.
  - Failed target returns startup failure.
  - Missing target returns existing missing-server style error.

Suggested error enum:

```rust
pub enum McpServerReadinessError {
    StillStarting { server: String },
    StartupFailed { server: String, error: String },
    Missing { server: String },
    Request(anyhow::Error),
}
```

If adding a public enum in `codex-mcp` is too heavy, use `anyhow` with stable messages, but tests should still distinguish still-starting.

### `core/src/session/mcp.rs`

Add session wrappers:

- `list_resources_if_ready`
- `list_resource_templates_if_ready`
- `read_resource_if_ready`
- `list_available_resources`
- `list_available_resource_templates`

Existing blocking wrappers remain for contexts that intentionally wait.

## Call-Site Changes

### MCP tool metadata

In `core/src/mcp_tool_call.rs`:

- Replace `manager.list_all_tools().await` in `lookup_mcp_tool_metadata()` with `manager.tool_info_if_available(server, tool_name)`.
- Replace `lookup_mcp_app_usage_metadata()` with `tool_info_if_available(server, tool_name)`.
- For connector description fallback, prefer cached connector metadata. If no cached connector metadata exists, use available connector listing, not full blocking discovery.

Expected behavior:

- Ready target tool metadata resolves even if another MCP server is pending.
- Pending target tool returns no metadata or a clear still-starting result, but does not block.

### Connector / plugin management

In `core/src/connectors.rs`:

- Replace default `list_all_tools().await` with `list_available_tools()`.
- Keep `force_refetch` as the only path that calls `hard_refresh_codex_apps_tools_cache().await`.
- If tools are empty and Codex Apps exists, bounded wait may remain, but only for Codex Apps, not all MCP.
- After bounded Codex Apps wait succeeds, reload with an available/server-specific API or hard refresh result, not global all-server wait.

In `core/src/tools/handlers/request_plugin_install.rs`:

- Use `manager.list_available_tools()` for initial accessible connector discovery.
- In `refresh_missing_requested_connectors()`, start with available tools.
- Only call `hard_refresh_codex_apps_tools_cache()` when expected connector ids are still missing and the request is specifically about Codex Apps/plugin connector discovery.

### MCP resource tools

Two acceptable implementation shapes:

1. **Expose only when safe**
   - In `spec_plan.rs`, register MCP resource tools only when at least one available MCP tool/server exists.
   - This is minimal but may hide resource-only MCP servers that expose no tools.

2. **Expose with nonblocking handlers**
   - Keep resource tools when MCP servers exist.
   - Change handlers to use available resource APIs that skip pending optional servers.
   - For specified pending server, return still-starting message.

Preferred: **Option 2**. It is more complete and handles resource-only servers. It requires manager-level available resource APIs.

### Spawned subagents

No required-server bypass.

Subagent first-turn behavior should be covered by the same `built_tools()` path and nonblocking metadata/resource/connector paths. Tests should exercise a real spawned child turn enough to prove no hidden spawn-specific wait remains.

## Data Flow

```text
McpConnectionManager
  ├─ blocking APIs: list_all_tools/list_all_resources/list_all_templates/client_by_name
  └─ available APIs: list_available_tools/tool_info_if_available/list_available_resources/...

Session turn construction
  └─ uses available tools

MCP tool execution metadata
  └─ uses tool_info_if_available

Connector/plugin metadata
  └─ uses list_available_tools; force refresh remains bounded and server-specific

MCP resource handlers
  └─ use available resource APIs; pending target yields still-starting
```

## Error Handling

- Pending optional server:
  - all-list APIs skip it.
  - specified-server APIs return still-starting message.
- Failed optional server:
  - all-list APIs skip and warn.
  - specified-server APIs return startup failure message.
- Required server:
  - unchanged during startup validation.
  - no ThreadSpawn-specific skip.
- Ready server request failure:
  - existing request error formatting remains.

## Testing Strategy

### `codex-mcp` unit tests

- `tool_info_if_available_skips_unrelated_pending_client`.
- `list_available_resources_skips_pending_client_without_awaiting`.
- `list_resources_if_ready_returns_still_starting_for_pending_server`.
- Existing `list_all_tools_blocks_while_client_is_pending_without_startup_snapshot` should remain as proof the blocking API is intentionally blocking.

### `codex-core` handler/unit tests

- `lookup_mcp_tool_metadata_does_not_wait_for_unrelated_pending_server`.
- `lookup_mcp_app_usage_metadata_does_not_wait_for_unrelated_pending_server`.
- `request_plugin_install_uses_available_tools_for_connector_discovery`.
- `list_mcp_resources_skips_pending_optional_server`.

### `codex-core` suite tests

- Parent turn:
  - One ready MCP server, one slow optional MCP server.
  - First request contains ready/snapshot tools only.
  - After slow server ready, later turn includes delayed tool.
- Spawned subagent:
  - Parent calls `spawn_agent`.
  - Child first model request starts without waiting for slow optional MCP.
  - Child first request omits slow optional tool.
- Required behavior:
  - Required MCP failure still fails startup or unsafe continuation according to existing behavior.

## Risks

- Resource-only servers may be hidden if implementation picks expose-only-when-available-tools. Prefer nonblocking resource handlers to avoid this.
- `list_available_tools()` derives availability from tool snapshots; resources do not currently have snapshots. Ready-only resource listing is acceptable for MVP.
- Connector discovery has user-facing UX implications; if a connector is still starting, the model should not see it until later turn or explicit refresh.
- Existing `codex-core` test suite currently has unrelated `ModelClient::stream` signature compile failures. Validation plan must record that if still present.

## Rollback

- Revert call-site changes to blocking APIs if regressions appear.
- Keep new manager helper APIs if harmless; they are additive and can remain unused.
- No config migration or persisted data changes are planned.
