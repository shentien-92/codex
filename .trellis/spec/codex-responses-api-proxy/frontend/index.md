# @openai/codex-responses-api-proxy 前端规范

这个包是原生 Codex Responses API proxy binary 的 npm 包装层。它是 Node 可执行包，
不是 UI 前端。

## 规范索引

| 文档                                  | 内容                          | 状态   |
| ------------------------------------- | ----------------------------- | ------ |
| [目录结构](./directory-structure.md)  | 包布局和 vendored binary 路径 | 已填写 |
| [组件规范](./component-guidelines.md) | 无组件层；可执行包装层约定    | 已填写 |
| [Hook 规范](./hook-guidelines.md)     | 无 React hooks；进程信号约定  | 已填写 |
| [状态管理](./state-management.md)     | 启动和 child-process 状态     | 已填写 |
| [质量规范](./quality-guidelines.md)   | 打包和运行时检查              | 已填写 |
| [类型安全](./type-safety.md)          | JavaScript 校验和路径约定     | 已填写 |

## 开发前检查清单

- 修改包装层行为前，先读
  `codex-rs/responses-api-proxy/npm/bin/codex-responses-api-proxy.js`。
- 修改包元数据或发布布局前，先检查
  `codex-rs/responses-api-proxy/npm/package.json`。
- 行为要和 `codex-rs/responses-api-proxy/README.md` 中记录的原生 proxy 保持一致。
- 不要在这个包里加入 React、浏览器或客户端应用模式。

## 验证

- 修改包装层时，如果原生 binary 可用，运行 bin 的 `--help` 之类的 smoke check。
- 只改元数据时，运行覆盖 JS/JSON/Markdown 的仓库格式化检查。
