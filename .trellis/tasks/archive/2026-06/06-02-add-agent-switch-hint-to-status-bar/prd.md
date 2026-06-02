# PRD: 在 status bar 增加 agent 切换提示

## 背景

Ralph 确认 macOS/Warp 中 `Option+Left/Right` 可以切换 agent 视窗，但提示目前只在
`/agent` picker 中出现。用户在正常聊天底部 status bar 里看不到快捷键。

## 目标

- 当 footer/status bar 显示 active agent label 时，同时显示 agent 切换提示。
- 提示使用现有快捷键定义派生，避免和实际 key binding 漂移。
- 内置 status line 和 command-backed status line 都应能看到提示。

## 非目标

- 不改变快捷键组合。
- 不新增 status line 配置项。
- 不影响没有 active agent label 的普通单线程 footer。

## 验收标准

- active agent label 单独显示时，footer 包含切换提示。
- active agent label 与 status line 同行显示时，footer 包含切换提示。
- 相关 snapshot 更新。
