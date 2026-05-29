# 状态管理

## Thread state

`Thread` 只保存最小 private state：

- `_exec`：process adapter；
- `_options`：global `CodexOptions`；
- `_threadOptions`：per-thread CLI settings；
- `_id`：新 thread 在收到 `thread.started` 前为 `null`，或由 `resumeThread(id)` 初始化。

通过只读 `id` getter 暴露 id。不要允许 callers 直接修改它。

## Turn state

`run()` 跟踪 per-turn local state：

- completed `ThreadItem[]`；
- 最新 agent message 作为 `finalResponse`；
- `Usage | null`；
- `ThreadError | null`。

这些状态只属于单个 turn。连续 `run()` 调用应通过 CLI thread id 延续，而不是手动 replay
SDK-side state。

## Input normalization

`normalizeInput()` 转换：

- string input → `{ prompt: input, images: [] }`；
- structured text entries → 用空行拼接的 prompt sections；
- local image entries → `--image` paths。

保持 text prompt 和 image paths 的分离。

## 常见错误

- 在 SDK 中存储 transcript；conversation continuity 归 CLI 所有。
- 从 `thread.started` 以外的来源更新 `_id`。
- `run()` 完成后，把 turn-local `items` 或 errors 保存在 `Thread` instance 上。
