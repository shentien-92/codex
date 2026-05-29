# 质量规范

## 运行时质量线

改动必须保留：

- ESM 语法和 top-level `await`；
- 直接把参数转发给原生 binary；
- inherited stdio；
- 对 `SIGINT`、`SIGTERM`、`SIGHUP` 的 signal forwarding；
- 正确镜像 exit code 和 signal；
- Linux、macOS、Windows 的 x64/arm64 平台覆盖。

## 依赖纪律

不要为包装层新增依赖。现有 Node built-ins 已足够：`node:child_process`、`path` 和
`url`。

## 打包检查

修改包元数据前，确认：

- `bin.codex-responses-api-proxy` 指向 `bin/codex-responses-api-proxy.js`；
- `files` 包含 `bin` 和 `vendor`；
- package manager pin 与 workspace 保持一致。

## 常见错误

- 让 wrapper 变成 proxy 行为的第二套实现。
- 添加 wrapper logs，破坏机器可读输出。
- 忘记 Windows `.exe` 路径处理。
