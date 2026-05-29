# 目录结构

## 包形态

`@openai/codex` 位于 `codex-cli/`，并且刻意保持很小：

- `codex-cli/package.json` 声明 npm 包元数据。
- `codex-cli/bin/codex.js` 是唯一发布出去的可执行入口。
- `codex-cli/scripts/` 包含打包和支持脚本，不在 package `files` 列表中发布。

这个包是 ESM 包（`"type": "module"`）。新增 JavaScript 应使用 ES module
import；只有在 ESM 中解析包元数据时，才像 `bin/codex.js` 一样使用
`createRequire()`。

## 入口归属

所有运行时包装逻辑都归 `codex-cli/bin/codex.js` 所有。这个文件只负责：

- 将 `process.platform` 和 `process.arch` 映射到 Rust target triple；
- 解析已安装的 optional native package，或回退到本地 `vendor/`；
- 构造子进程环境；
- 启动原生 `codex` binary，并镜像它的退出状态。

不要在这个包里创建通用 frontend 目录、组件树或浏览器 bundle。真正的用户界面由
`codex-rs/` 下的原生 Rust CLI/TUI 实现。

## 真实示例

- 平台包映射：`codex-cli/bin/codex.js`
- npm 包元数据和 package `files`：`codex-cli/package.json`
- workspace 成员关系：`pnpm-workspace.yaml`

## 常见错误

- 在 `codex-cli/` 下新增运行时文件，却忘了只有 `bin/codex.js` 会被 package
  `files` 发布。
- 在这里复制原生 CLI 逻辑，而不是委托给 Rust binary。
- 因为 Trellis 把这一层标成 `frontend` 就套用浏览器约定；这个包实际是 Node CLI
  包装层。
