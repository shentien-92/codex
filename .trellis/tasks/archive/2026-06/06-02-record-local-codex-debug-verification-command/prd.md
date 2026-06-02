# PRD: 记录本地 Codex debug 验证命令

## 背景

Ralph 重启本地 Codex 时会直接运行 `codex` 命令。排查 TUI/Rust 修复时，如果只说明
`cargo run` 或 `just codex`，容易忽略当前 shell 中 `codex` 是否已经链接到并重新构建了
本仓库的 debug binary。

## 目标

- 在 Trellis spec 中记录：验证本地 Codex 修复前，先确认 `codex` 命令指向当前 repo 的
  `codex-rs/target/debug/codex`。
- 记录：源码改动后需要先重建 debug binary，再让 Ralph 通过 `codex -c` 重启验证。
- 记录：如果重启后现象没变化，优先怀疑 binary 未重建或命令路径不对。

## 非目标

- 不修改 Codex 功能代码。
- 不改变 npm 包装层或 Rust 构建脚本。

## 验收标准

- `.trellis/spec/codex/frontend/quality-guidelines.md` 包含本地 debug 验证注意事项。
- 规范包含可直接执行的检查命令。
