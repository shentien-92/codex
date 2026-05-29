# Hook 规范

## 概览

`@openai/codex` 没有 React hooks。这里相关的生命周期 hook 是 Node process
events 和 child-process signal forwarding。

## 进程生命周期

`codex-cli/bin/codex.js` 使用异步 `spawn()`，这样原生 binary 运行期间 Node 仍可
接收信号。保持这个模式。除非明确重新设计并测试信号行为，否则不要替换成
`spawnSync()`。

信号转发遵循现有模式：

- 注册 `SIGINT`、`SIGTERM`、`SIGHUP` handler；
- 如果 child 已经 killed，则跳过转发；
- 捕获并忽略 `child.kill()` 失败；
- 如果 child 因 signal 退出，父进程重新发出同一个 signal。

## 环境变量 hook

包装层会注入包管理标记：

- `CODEX_MANAGED_BY_BUN` 或 `CODEX_MANAGED_BY_NPM`；
- `CODEX_MANAGED_PACKAGE_ROOT`；
- 当 native package 包含 path directory 时，前置更新 `PATH`。

修改启动流程时必须保留这些变量。它们用于让原生 CLI 知道自己是从 npm 包启动的。

## 常见错误

- 在 signal handler 中直接调用 `process.exit()`，导致 child 还没退出父进程就结束。
- 丢失 native package support directory 的 `PATH` 更新。
- 把 package-manager 检测当成依赖解析器；它只用于面向用户的重装提示和管理标记。
