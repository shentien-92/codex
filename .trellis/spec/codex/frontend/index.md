# @openai/codex 前端规范

这个包是原生 Codex CLI 的 npm 分发包装层，不是浏览器前端，也不是 React
应用。这里的改动应当按 `codex-cli/bin/codex.js` 的打包和运行时入口来处理。

## 规范索引

| 文档                                  | 内容                                   | 状态   |
| ------------------------------------- | -------------------------------------- | ------ |
| [目录结构](./directory-structure.md)  | 包布局和归属文件                       | 已填写 |
| [组件规范](./component-guidelines.md) | 无组件层；CLI 包装层约定               | 已填写 |
| [Hook 规范](./hook-guidelines.md)     | 无 React hooks；进程和信号生命周期约定 | 已填写 |
| [状态管理](./state-management.md)     | 包装进程中的运行时状态                 | 已填写 |
| [质量规范](./quality-guidelines.md)   | 打包、进程和测试要求                   | 已填写 |
| [类型安全](./type-safety.md)          | JavaScript 数据形状约定                | 已填写 |

## 开发前检查清单

- 修改包装层行为前，先读 `codex-cli/bin/codex.js`。
- 修改包元数据前，先检查 `codex-cli/package.json` 中的 `files`、`bin`、engine
  和 repository directory。
- 如果修改 vendored binary 查找逻辑，要同时对照 `resolveNativePackage()` 中的
  package layout 分支和 legacy layout 分支。
- 保持包装层为 ESM-only，并兼容包里声明的 Node engine。
- 不要在这个包里加入 UI framework、浏览器或 React 模式。

## 验证

- 有 package-level 检查覆盖时，运行能覆盖改动行为的检查。
- 只改打包相关文件时，至少运行覆盖 JS 和 JSON 的仓库格式化检查。
