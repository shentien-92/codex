# MCP startup nonblocking gap completion

## Goal

补完旧任务 `05-29-mcp-startup-nonblocking-prd` 的遗漏功能，让 optional MCP server 启动真正成为后台 readiness 过程，而不是在 metadata、resource、connector、plugin-install 或 spawned subagent 路径中通过 `list_all_tools().await` 等全量等待重新卡住主会话或子会话。

本任务不是重新实现完整旧 PRD，而是针对验收发现的缺口收口：保留已经完成的 TUI slash-command / resume 改动，补齐 MCP runtime 管理路径的非阻塞语义和测试。

## Source Context

- 原 PRD：`.trellis/tasks/archive/2026-06/05-29-mcp-startup-nonblocking-prd/prd.md`
- 验收结论：未完成。
- 独立 review 发现：
  - `core/src/mcp_tool_call.rs` 的 MCP approval / app metadata lookup 仍调用 `list_all_tools().await`。
  - `core/src/tools/spec_plan.rs` 在没有可用 MCP tool 时仍可能暴露 MCP resource tools；resource handlers 会调用 blocking resource list。
  - `core/src/connectors.rs` 与 `core/src/tools/handlers/request_plugin_install.rs` 仍有全量 blocking MCP tool list。
  - 测试缺少 session/turn 级 E2E，尤其是 spawned subagent 与 delayed MCP later-turn readiness。

## What I Already Know

- `McpConnectionManager::list_available_tools()` 已存在，语义是只返回 ready 或 startup snapshot-backed tools，不等待 pending server。
- `McpConnectionManager::list_all_tools().await` 会等待每个 managed client 的 `listed_tools()`，因此一个无关 slow/pending MCP 会拖住整个调用。
- `Session::built_tools()` 当前已经使用 `list_available_tools()` 构造首轮工具列表，这覆盖了普通 turn 的主要 model-visible tool path。
- required MCP server 语义必须保持严格。不能通过跳过 ThreadSpawn required startup wait 解决卡顿；这会削弱 `required = true` 的保证。
- optional MCP server pending 且没有 snapshot/cache 时，应从当前 turn 可见工具中省略，待 ready 后在 later turn 出现。
- spawned subagent 会初始化自己的 session/tool router，所以 main TUI-only 修复不足以覆盖问题。

## Requirements

### Nonblocking MCP Tool Metadata

- MCP tool approval metadata lookup 必须避免等待无关 pending MCP server。
- MCP app usage metadata lookup 必须避免等待无关 pending MCP server。
- 如果目标 MCP server/tool 当前不可用但仍在启动，应返回明确的 unavailable/still-starting 语义，不能因为其他 MCP pending 而阻塞。
- metadata lookup 应优先使用当前可用 tool snapshot/cache，或实现 server/tool-specific 非阻塞查询。

### Nonblocking MCP Resource Tools

- MCP resource tools 不应仅因为配置了 MCP server 就暴露；至少需要有 ready 或 snapshot-backed MCP capability，或能在调用时给出明确 still-starting 响应。
- `list_mcp_resources`、`list_mcp_resource_templates`、`read_mcp_resource` 不应被无关 pending optional MCP server 卡住。
- 对全量 resource list，pending optional server 应被跳过或以非阻塞状态报告。
- 对指定 pending server/resource 的读取，应给模型/用户可理解的 “server still starting / resource unavailable yet” 结果，而不是 generic timeout 或全局 task-running rejection。

### Nonblocking Connector / Plugin Management Paths

- connector discovery 默认路径应使用 available tools，不等待所有 MCP server。
- plugin install request / missing connector refresh 默认路径应使用 available tools。
- 只有显式 force refresh 或 Codex Apps 特定等待场景才允许 bounded wait，而且等待范围必须限定到相关 server，不允许全局等待所有 MCP。
- 任何 bounded wait 都必须有可测试的 timeout 行为，并且不影响无关 ready MCP tool 的调用。

### Spawned Subagent Semantics

- spawned subagent 的 first turn 可以在 slow optional MCP startup 期间开始。
- spawned subagent 的 first model request 只包含 ready 或 snapshot-backed MCP tools。
- pending optional MCP tools 在 subagent later turn 中 ready 后可见。
- required MCP server 对 spawned subagent 仍保持现有 strict behavior；required failure 不能被 silently ignored。

### Required MCP Semantics

- `required = true` 的 MCP server 仍必须按现有 required startup behavior 阻止 unsafe continuation。
- 本任务不得通过跳过 required wait、降级 required 为 optional、或吞掉 required failure 来获得非阻塞效果。
- 如果需要改 required handling，必须明确区分 optional 和 required，并提供测试证明 required 行为不变。

## Acceptance Criteria

- [ ] `mcp_tool_call.rs` 中 MCP approval metadata lookup 不再调用全量 blocking `list_all_tools().await`。
- [ ] `mcp_tool_call.rs` 中 MCP app usage metadata lookup 不再调用全量 blocking `list_all_tools().await`。
- [ ] 存在回归测试：两个 MCP server，一个 ready target tool，一个 unrelated pending optional server；调用 ready target tool 不等待 pending server。
- [ ] MCP resource tools 不会因 `has_mcp_servers == true` 且 available tool list 为空而暴露会阻塞的全量 resource handlers，或 handlers 本身实现非阻塞 skip/pending 状态。
- [ ] 存在回归测试：pending optional MCP server 不会阻塞 `list_mcp_resources` / `list_mcp_resource_templates` 路径。
- [ ] connector discovery 默认不使用全量 blocking `list_all_tools().await`。
- [ ] plugin install / missing connector refresh 默认不使用全量 blocking `list_all_tools().await`。
- [ ] 存在回归测试：connector/plugin discovery 在无关 MCP server pending 时仍能基于 ready/snapshot tools 返回。
- [ ] spawned subagent first turn 在 slow optional MCP startup 期间能开始，不等待 every optional MCP server。
- [ ] spawned subagent first model request 省略 pending optional MCP tools。
- [ ] pending optional MCP server ready 后，later turn 的 tool list 包含新增 MCP tools。
- [ ] required MCP server failure 仍按当前 required semantics 阻止 unsafe continuation。
- [ ] 不新增 ThreadSpawn-specific required MCP bypass。
- [ ] `just fmt` 已运行。
- [ ] 针对修改 crate 运行定向测试；若 `codex-core` 现有测试签名问题阻塞全量 `just test -p codex-core`，需记录阻塞原因并至少运行能覆盖新增测试的更窄命令或说明无法运行。

## Out Of Scope

- 不重做已完成的 TUI slash-command gating 与 same-cwd resume hardening，除非测试证明仍直接影响本任务。
- 不隐藏 MCP startup status。
- 不把 delayed MCP tools 动态注入已经发送的同一 model request。
- 不重启或自动修复 failed MCP server。
- 不改 MCP config/OAuth 设计。
- 不删除或改写 Ralph 的用户/项目 MCP 配置。
- 不禁用 required MCP semantics。

## Technical Notes

- 重点文件：
  - `codex-rs/codex-mcp/src/connection_manager.rs`
  - `codex-rs/core/src/mcp_tool_call.rs`
  - `codex-rs/core/src/connectors.rs`
  - `codex-rs/core/src/tools/handlers/request_plugin_install.rs`
  - `codex-rs/core/src/tools/spec_plan.rs`
  - `codex-rs/core/src/tools/handlers/mcp_resource/*`
  - `codex-rs/core/src/session/turn.rs`
  - `codex-rs/core/src/tools/handlers/multi_agents*`
- Preferred implementation direction:
  - Add nonblocking helper APIs on `McpConnectionManager` for available tool lookup and available resource capability.
  - Replace broad `list_all_tools().await` in turn-time metadata paths with available/server-specific lookup.
  - Keep blocking APIs only for explicit admin/refresh contexts where waiting is intentional and bounded.
  - Add tests before or alongside implementation so the previous partial completion cannot regress unnoticed.

## Definition Of Done

- PRD gap findings are addressed in code or explicitly moved out of scope with written rationale.
- Required MCP behavior is proven unchanged.
- Optional MCP pending behavior is nonblocking across turn construction, metadata lookup, connector/plugin management, resource tools, and spawned subagent first turn.
- Focused regression tests exist for each previously missed path.
