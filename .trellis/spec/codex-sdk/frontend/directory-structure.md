# 目录结构

## Public API 布局

面向消费者的 SDK surface 位于 `sdk/typescript/src/`：

- `index.ts` re-export public classes 和 types。
- `codex.ts` 定义 `Codex` client。
- `thread.ts` 定义 `Thread`、`Turn`、`RunResult`、`StreamedTurn`、
  `RunStreamedResult`、`Input` 和 `UserInput`。
- `codexOptions.ts`、`threadOptions.ts`、`turnOptions.ts` 定义 public option
  objects。
- `events.ts` 和 `items.ts` 定义发给消费者的 discriminated unions。

Samples 位于 `sdk/typescript/samples/`，应保持短小、直接，并与 README examples
一致。

## Export 规则

Public consumer APIs 应从 `src/index.ts` 导出。Process resolution、config
flattening、test-only utilities 等 internal helpers 不应导出，除非任务明确要求公开。

## 文档位置

面向用户的 SDK 用法写在 `sdk/typescript/README.md` 和 samples 中。不要把通用产品文档
新增到 repo-level `docs/` 目录。

## 真实示例

- Main client：`sdk/typescript/src/codex.ts`
- Thread methods：`sdk/typescript/src/thread.ts`
- README examples：`sdk/typescript/README.md`
- Structured output samples：`sdk/typescript/samples/structured_output.ts`

## 常见错误

- 新增 public type 但忘了从 `src/index.ts` 导出。
- 更新 examples 却没有为行为补充 matching tests。
- 把它当成 browser SDK；当前 SDK 包装本地 CLI，并要求 Node runtime。
