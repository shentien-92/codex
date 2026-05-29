# @openai/codex-sdk 后端规范

SDK 后端层是 Node 运行时适配层：负责启动 Codex CLI、序列化 CLI/config 参数、流式读取
JSONL events，并暴露可测试的进程边界行为。

## 规范索引

| 文档                                   | 内容                                 | 状态   |
| -------------------------------------- | ------------------------------------ | ------ |
| [目录结构](./directory-structure.md)   | Source、tests、build 和 samples 布局 | 已填写 |
| [数据库规范](./database-guidelines.md) | 无数据库层；持久化边界               | 已填写 |
| [错误处理](./error-handling.md)        | 进程、JSONL、config 和 turn 错误     | 已填写 |
| [质量规范](./quality-guidelines.md)    | Lint、test、build 和 API 要求        | 已填写 |
| [日志规范](./logging-guidelines.md)    | SDK 运行时日志和噪声规则             | 已填写 |

## 开发前检查清单

- 先读拥有该行为的源文件：`src/exec.ts`、`src/thread.ts`、option type 文件，或
  event/item type 文件。
- 读取 `sdk/typescript/tests/` 中对应的 Jest tests。
- 保持 `tsconfig.json` 中的严格 TypeScript 设置，尤其是 `strict`、`noImplicitAny`
  和 `noUncheckedIndexedAccess`。
- 保持 SDK ESM-only，并以 Node 18 为 target。
- 不要向 SDK 添加 persistence、database 或 service framework 模式。

## 验证

在 `sdk/typescript/` 下运行 package scripts：

- `pnpm run lint`
- `pnpm test`
- `pnpm run build`
