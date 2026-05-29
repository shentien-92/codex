# 质量规范

## Public API 质量

SDK 是发布的 TypeScript 包。改动应保留：

- 稳定的 exported class 和 type names；
- 清晰的 option objects，而不是 positional flags；
- events 和 items 使用 discriminated unions；
- 面向用户行为有 README 和 sample 覆盖；
- 新 options、event handling 或 input forms 有 test coverage。

## 文档质量

README examples 应在概念上能用 exported API 编译，避免引用 undocumented internals。
Samples 应短小，并聚焦一个场景。

新增 public option 时，要记录：

- 它传入的位置（`CodexOptions`、`ThreadOptions` 或 `TurnOptions`）；
- 它映射到什么 CLI/config 行为；
- 是否存在 precedence rules。

## 测试要求

使用现有 tests 作为消费者行为来源：

- `tests/run.test.ts` 覆盖 `run()`、`runStreamed()`、resume、options、images 和
  structured output；
- `tests/abort.test.ts` 覆盖 cancellation；
- `tests/exec.test.ts` 覆盖 process-boundary behavior。

## 常见错误

- 发布 public API 变更时只有 implementation tests，没有更新 consumer example。
- 新增 event/item variants，却没有完整 sample/test handling。
- 让 SDK 依赖 browser，或假设 DOM globals 存在。
