# 类型安全

## Public types

保持 public API types 显式且收窄：

- option unions，例如 `SandboxMode`、`ApprovalMode`、`WebSearchMode` 和
  `ModelReasoningEffort`；
- `ThreadEvent` 和 `ThreadItem` 使用 discriminated unions；
- 当有助于文档清晰时，保留 named result aliases（`RunResult`、
  `RunStreamedResult`）。

避免暴露 `any`。对不可信 payloads 使用 `unknown`，例如 MCP tool arguments 和
structured result fields。

## Event contracts

Events 和 items 镜像 Rust exec JSONL contracts。修改 contract 时：

- 更新 `events.ts` 或 `items.ts` 中的 TypeScript union；
- 必要时更新 `thread.ts` 中的 parsing 或 collection logic；
- 更新断言 streamed 或 completed items 的 tests；
- 确认 Rust producer 发出相同的 discriminants 和 field names。

## Optional values

已知缺失状态使用 `null`，例如 `Thread.id` 和 `usage`。item 仍在 in progress 时会省略的
字段使用 optional properties，例如 `exit_code?`、`result?` 和 `error?`。

## 常见错误

- 当 CLI 支持有限集合时，把 option fields 放宽成 `string`。
- 第一轮开始前把 `thread.id` 当成非空值。
- 在启用 `noUncheckedIndexedAccess` 的 tests 中，不 guard 或 assert defined 就访问
  arrays。
