# 质量规范

## TypeScript 质量线

遵守这个包的严格 compiler settings：

- 避免 `any`；对 public types 使用显式类型，对不可信边界使用 `unknown`；
- 因为启用了 `noUncheckedIndexedAccess`，访问可能 undefined 的 array indexes 时要处理；
- public option unions 保持收窄，例如 `ApprovalMode`、`SandboxMode` 和
  `WebSearchMode`；
- 合适时使用 type-only imports。

## 测试模式

沿用现有 Jest helper patterns：

- process-spawn 行为：像 `tests/exec.test.ts` 一样 mock `node:child_process`；
- end-to-end SDK 行为：像 `tests/run.test.ts` 一样使用 `startResponsesTestProxy()`
  和 `createMockClient()`；
- 尽量用 `toEqual()` 比较完整对象；
- 测试应与调用者环境隔离，除非测试明确覆盖 environment inheritance。

## Build 和 lint

SDK 改动在 `sdk/typescript/` 下运行：

- `pnpm run lint`
- `pnpm test`
- `pnpm run build`

修改 Markdown、JSON 或 TypeScript 格式时，使用 `pnpm run format` 或 `format:fix`。

## Public API 纪律

SDK 是发布包。除非任务明确要求，避免破坏 exported names、option fields、event
discriminants 或 item shapes。

## 常见错误

- 新增 CLI flag path，却没有测试检查 spawned arguments。
- 新增 event/item variants，却没有同步更新 `events.ts`/`items.ts` 和相关 stream
  tests。
- 让测试依赖开发者真实的 Codex home 或 plugin state。
