# 组件规范

## 概览

这个包没有 UI 组件系统。没有 React components、props、JSX，也没有浏览器渲染层。
应把这里的可执行入口视为围绕原生 `codex` binary 的小型进程组件。

## 包装层结构

遵循 `codex-cli/bin/codex.js` 现有的顶层流程：

1. 根据 `process.platform` 和 `process.arch` 推导 target triple；
2. 解析匹配的 optional package 或本地 vendor fallback；
3. 准备 `PATH` 和管理用环境变量；
4. 用 `stdio: "inherit"` 启动原生 binary；
5. 转发进程信号并镜像子进程退出结果。

辅助函数应靠近它们支持的行为。现有辅助函数包括 `resolveNativePackage()`、
`getUpdatedPath()` 和 `detectPackageManager()`。

## 公开面

这个包的公开面是 `codex-cli/package.json` 中声明的 `codex` bin。不要在这里新增
导出的 JS API。面向消费者的 TypeScript API 应放在 `sdk/typescript/`。

## 样式和可访问性

这个包没有样式或可访问性规则。终端输出由原生 binary 负责。包装层除了 fatal
spawn error 或可执行的安装错误外，应避免打印内容。

## 常见错误

- 向 `codex-cli/` 添加 React 或 DOM 抽象。
- 在包装层处理终端渲染，而不是通过 inherited stdio 交给原生 binary。
- 在镜像子进程结果之前让父 Node 进程提前退出。
