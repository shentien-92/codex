# 目录结构

## 包形态

`@openai/codex-sdk` 位于 `sdk/typescript/`。

重要文件：

- `src/index.ts` 导出公开 SDK surface。
- `src/codex.ts` 拥有 `Codex` client object。
- `src/thread.ts` 拥有 thread state、`run()`、`runStreamed()` 和 input
  normalization。
- `src/exec.ts` 拥有 Codex CLI resolution、process spawning、config
  serialization 和 JSONL line streaming。
- `src/*Options.ts` 文件定义公开 option shapes。
- `src/events.ts` 和 `src/items.ts` 镜像 Rust exec 层的 JSONL event/item
  contracts。
- `tests/` 包含 Jest integration 和 process-boundary tests。
- `samples/` 包含面向用户的 TypeScript examples。

## 模块边界

Process-spawn 和 CLI-argument 逻辑应留在 `src/exec.ts`。Conversation state 和
event interpretation 应留在 `src/thread.ts`。Public option types 放在小型专用文件
中，不要塞进实现模块。

新增 public export 时，要更新 `src/index.ts`，并确认 generated declaration output 仍
包含在 build 产物里。

## Build 和运行时

这个包是 ESM-only：

- `package.json` 有 `"type": "module"`；
- `tsup.config.ts` 从 `src/index.ts` 输出 ESM 和 declarations；
- `tsconfig.json` 使用 `moduleResolution: "bundler"`，target 为 ES2022。

## 真实示例

- Process adapter：`sdk/typescript/src/exec.ts`
- Thread abstraction：`sdk/typescript/src/thread.ts`
- Test proxy：`sdk/typescript/tests/responsesProxy.ts`
- Mock process tests：`sdk/typescript/tests/exec.test.ts`

## 常见错误

- 把 process-spawn 行为混进 `Thread`，而不是留在 `CodexExec`。
- 新增 public API types 却忘了从 `src/index.ts` 导出。
- 在 SDK 中创建 database 或 persistence layer；持久化 sessions 由 Codex CLI 在
  `~/.codex/sessions` 下管理。
