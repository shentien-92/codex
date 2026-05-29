# 质量规范

## 包装层质量线

包装层要保持简单、稳定、可预测。改动必须保留：

- ESM imports 和 top-level `await`；
- inherited stdio 的异步 child-process 执行；
- Linux、macOS、Windows 的 x64/arm64 平台覆盖；
- package-layout 和 legacy-layout 两种 binary 查找；
- signal forwarding 和 exit-code mirroring。

## 依赖纪律

不要为 Node 已经提供的包装逻辑新增依赖。现有代码使用 `node:child_process`、`fs`、
`node:module`、`path` 和 `url`。

## 打包检查

修改包元数据前，确认：

- `bin.codex` 仍指向 `bin/codex.js`；
- `files` 仍包含所有必须发布的运行时文件；
- package manager pin 与 workspace 保持一致。

## 常见错误

- 新增 helper script 但运行时需要发布时忘记加入 `files`。
- 重排 `spawn()` 或 signal handling，破坏 Ctrl-C 行为。
- 把属于 `codex-rs/` 的原生 CLI 行为扩展到这个包装层。
