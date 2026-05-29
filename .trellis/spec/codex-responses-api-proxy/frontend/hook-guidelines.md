# Hook 规范

## 概览

这个包没有 React hooks。生命周期处理仅限于围绕原生 proxy child process 的 Node
process events。

## 信号转发

遵循现有 `forwardSignal()` 模式：

- 处理 `SIGINT`、`SIGTERM`、`SIGHUP`；
- child 已 killed 时跳过转发；
- 捕获并忽略 `child.kill()` 失败；
- child 因 signal 退出时，父进程重新发出同一个 signal。

这样可以让 Ctrl-C 和 service manager 的终止行为与原生进程保持一致。

## Child process hooks

包装层监听：

- `error`：打印 spawn error 并以非零状态退出；
- `exit`：解析 child result，并镜像 code 或 signal。

保持 stdout/stderr inherited。除非包设计明确改变，否则不要拦截输出。

## 常见错误

- 处理 `exit` 时丢失终止原因是 signal 还是 exit code。
- 切换到 buffered stdio，导致 proxy 输出延迟。
- 给只负责启动进程的包添加 framework-style lifecycle hooks。
