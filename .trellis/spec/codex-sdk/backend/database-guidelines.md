# 数据库规范

## 概览

TypeScript SDK 没有 database layer、ORM、migrations 或 repository pattern。不要为了
SDK 运行时行为引入这些结构。

## 持久化边界

Conversation persistence 归 Codex CLI 所有，不归这个包所有：

- `Codex.startThread()` 创建内存中的 `Thread`，首次收到 `thread.started` event 前没有
  id。
- `Codex.resumeThread(id)` 用 caller 提供的 id 创建 `Thread`。
- persisted session files 位于 CLI 管理的 `~/.codex/sessions`，这点已在
  `sdk/typescript/README.md` 中说明。

SDK 应把 `threadId` 传给 CLI，并在收到 `thread.started` 时更新内存中的 id；不要直接
读写 session files。

## 测试数据

测试使用内存 HTTP servers 和临时文件系统 fixtures：

- `tests/responsesProxy.ts` 用本地 SSE server 记录 request bodies。
- `tests/exec.test.ts` 在 `tmpdir()` 下构造临时 vendor layouts。
- `tests/setupCodexHome.ts` 为测试配置隔离的 Codex home state。

优先使用这种方式，不要引入 persistent fixtures 或 external databases。

## 常见错误

- 直接读取 CLI session files，而不是使用 `resumeThread(id)`。
- 为规避 process startup 行为而添加 SQLite 或 file-backed caches。
- 测试里使用真实网络服务，而不是本地 response proxy pattern。
