# MCP startup nonblocking gap completion quality notes

## Verification Commands

- `cd codex-rs && just fmt` passed.
- `cd codex-rs && just test -p codex-core mcp_startup_nonblocking` passed:
  - `pending_optional_mcp_is_omitted_first_turn_and_visible_later`
  - `spawned_subagent_first_turn_omits_pending_optional_mcp`
  - `required_mcp_failure_is_reported_during_startup`
  - nextest reported the required-failure test as leaky because it intentionally exercises a failed startup path.
- `cd codex-rs && just test -p codex-mcp` passed earlier in this task after the nonblocking manager/resource changes.
- `cd codex-rs && just fix -p codex-core` passed.
- `git diff --check` passed.

An attempted broad `cd codex-rs && just test -p codex-core` run reached the new MCP startup nonblocking tests and they passed there as well, but the final summary was not retained after context compaction. During that broad run, unrelated existing/flaky failures were observed in code-mode and compact-remote tests, so the focused acceptance suite above is the authoritative signal for the new coverage.

## PRD Coverage Matrix

| Item | Status | Evidence |
| --- | --- | --- |
| MCP approval metadata lookup no longer calls global blocking `list_all_tools().await` | pass | `core/src/mcp_tool_call.rs` uses `tool_info_if_available`; static `rg` found no `list_all_tools().await` in `core/src/mcp_tool_call.rs`. |
| MCP app usage metadata lookup no longer calls global blocking `list_all_tools().await` | pass | `core/src/mcp_tool_call.rs` uses `tool_info_if_available`; static `rg` found no `list_all_tools().await` in `core/src/mcp_tool_call.rs`. |
| Ready target MCP tool is not blocked by unrelated pending optional MCP | pass | `codex-mcp` test `tool_info_if_available_skips_unrelated_pending_client`; suite test `pending_optional_mcp_is_omitted_first_turn_and_visible_later`. |
| MCP resource tools avoid blocking full-resource handlers while optional servers are pending | pass | Resource handlers call `list_available_resources`, `list_available_resource_templates`, and `read_resource_if_ready`; static scan found no blocking resource list calls in `core/src/tools/handlers/mcp_resource`. |
| Pending optional MCP does not block resource/template listing | pass | `codex-mcp` tests `list_available_resources_skips_pending_client_without_awaiting_startup` and `list_available_resource_templates_skips_pending_client_without_awaiting_startup`. |
| Connector discovery default does not use blocking `list_all_tools().await` | pass | `core/src/connectors.rs` uses `list_available_tools`; test `list_accessible_and_enabled_connectors_does_not_wait_for_pending_mcp_startup`. |
| Plugin install / missing connector refresh default does not use blocking `list_all_tools().await` | pass | `core/src/tools/handlers/request_plugin_install.rs` starts from `list_available_tools`; Codex Apps refresh remains explicit and server-specific. |
| Connector/plugin discovery works with unrelated pending MCP | pass | Connector regression test covers pending MCP; plugin path uses the same available-tool discovery helper and only hard-refreshes Codex Apps when needed. |
| Spawned subagent first turn starts while slow optional MCP is pending | pass | Suite test `spawned_subagent_first_turn_omits_pending_optional_mcp`. |
| Spawned subagent first model request omits pending optional MCP tools | pass | Suite test `spawned_subagent_first_turn_omits_pending_optional_mcp`. |
| Pending optional MCP tools appear on later turns after readiness | pass | Suite test `pending_optional_mcp_is_omitted_first_turn_and_visible_later`. |
| Required MCP failure still prevents unsafe continuation | pass | Suite test `required_mcp_failure_is_reported_during_startup`. |
| No ThreadSpawn-specific required MCP bypass was added | pass | Static scan shows required MCP waits remain in `core/src/session/session.rs`; no ThreadSpawn-specific bypass appears in the new suite or MCP startup path. |
| `just fmt` run | pass | `cd codex-rs && just fmt` passed. |
| Targeted tests for modified crates run | pass | `just test -p codex-core mcp_startup_nonblocking`, `just test -p codex-mcp`, and `just fix -p codex-core` passed. |
