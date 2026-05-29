# @openai/codex-sdk 前端规范

SDK 没有 React 或浏览器 UI。这个 frontend layer 记录面向消费者的 TypeScript API
形态：classes、public option objects、event types、samples，以及应用开发者会导入的
README examples。

## 规范索引

| 文档                                  | 内容                                 | 状态   |
| ------------------------------------- | ------------------------------------ | ------ |
| [目录结构](./directory-structure.md)  | Public API、samples 和 tests         | 已填写 |
| [组件规范](./component-guidelines.md) | 无 UI components；class/API 约定     | 已填写 |
| [Hook 规范](./hook-guidelines.md)     | 无 React hooks；async generator 约定 | 已填写 |
| [状态管理](./state-management.md)     | Thread 和 turn state                 | 已填写 |
| [质量规范](./quality-guidelines.md)   | API、docs 和 test 要求               | 已填写 |
| [类型安全](./type-safety.md)          | Public type 和 event contract 约定   | 已填写 |

## 开发前检查清单

- 修改 public API 行为前，先读 `sdk/typescript/src/index.ts`、`src/codex.ts` 和
  `src/thread.ts`。
- 修改面向用户的用法时，先读 `sdk/typescript/README.md` 和 samples。
- 读取 `sdk/typescript/tests/run.test.ts`，确认消费者行为预期。
- 保持 examples 和 public types 同步。
- 不要添加 React、DOM、browser-only APIs 或 framework hooks。

## 验证

在 `sdk/typescript/` 下运行：

- `pnpm run lint`
- `pnpm test`
- `pnpm run build`
