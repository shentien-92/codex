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

## 本地 debug 验证

Ralph 重启本地 Codex 时默认直接运行 `codex` 或 `codex -c`。验证 `codex-rs/` 的
TUI/Rust 修复前，必须先确认这个命令实际加载的是当前仓库的 debug binary，而不是旧的
全局安装或未重建产物。

推荐检查顺序：

```bash
command -v codex
ls -l "$(command -v codex)"
readlink "$(command -v codex)"
stat -f '%Sm %N' codex-rs/target/debug/codex
```

期望路径应指向当前仓库的 `codex-rs/target/debug/codex`。源码改动后，先在仓库根目录
运行一次：

```bash
just codex --version
```

这会通过 `cargo run --bin codex` 重建 debug binary。重建完成后，再让 Ralph 用
`codex -c` 重启验证。如果重启后现象完全没变，优先排查 `codex` 的软链目标、binary
mtime，以及是否启动了旧进程。

## 常见错误

- 新增 helper script 但运行时需要发布时忘记加入 `files`。
- 重排 `spawn()` 或 signal handling，破坏 Ctrl-C 行为。
- 把属于 `codex-rs/` 的原生 CLI 行为扩展到这个包装层。
- 修了 `codex-rs/` 源码后只让 Ralph 重启，却没有先重建 `codex-rs/target/debug/codex`。
