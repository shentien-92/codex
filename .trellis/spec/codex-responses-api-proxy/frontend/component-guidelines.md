# 组件规范

## 概览

这个包没有 UI 组件。唯一的运行时组件是启动原生 proxy binary 的 Node bin 包装层。

## 包装层结构

保持 `bin/codex-responses-api-proxy.js` 只负责：

1. 通过 `determineTargetTriple()` 推导 target triple；
2. 构造 vendored binary 路径；
3. 用 inherited stdio 启动原生 proxy；
4. 转发终止信号；
5. 镜像 child process 的退出结果。

不要添加 UI component abstractions、props objects、JSX 或 DOM 逻辑。

## 公开面

公开 npm 面是 `package.json` 中声明的 `codex-responses-api-proxy` binary。CLI
options 和面向用户的行为应在原生 proxy 中实现，不应放在包装层。

## 样式和可访问性

这里没有样式或可访问性层。终端 help 和 diagnostics 由原生 binary 负责。

## 常见错误

- 在包装层解析 options，而不是原样转发 `process.argv` 给原生 proxy。
- 打印 wrapper-level messages，干扰机器可读的 proxy 输出。
- 在这个包里创建共享 UI helper。
