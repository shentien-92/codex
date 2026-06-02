# PRD: 修复 Mac agent 视窗快捷键不生效

## 背景

Ralph 在 macOS 本地 Codex 中 spawn subagent 后，status bar 已能从
`agents 0` 更新为非零，但 `Option+Left/Right` 和 `Option+b/f` 都无法切换 agent
视窗。

## 问题判断

快捷键切换依赖 `App.agent_navigation` 中存在可遍历的 thread 列表。当前
`<subagent_notification>` 路径只更新了 `status_line_agents`，没有把 subagent
登记进 `agent_navigation`，也没有确保主线程在遍历列表里。因此即使 status bar 有
agent 数量，快捷键仍可能没有任何可切换目标。

## 目标

- 解析 `<subagent_notification>` 后同时同步 status line 和 `agent_navigation`。
- 当通知中的 `agent_path` 可解析为 `ThreadId` 时，把它作为 subagent 线程登记到
  navigation。
- 确保当前 primary/main thread 也进入 navigation，便于从主线程快捷键切到 subagent。
- 保持 `/agent` picker 和快捷键使用同一份 navigation 状态。

## 非目标

- 不改变快捷键组合。
- 不引入新的 agent UI。
- 不改变 subagent tool 协议。

## 验收标准

- status bar 仍能展示 subagent 数量。
- 收到 `<subagent_notification>` 后，`agent_navigation` 至少包含主线程和该 subagent。
- 从主线程按 agent next/previous 快捷键能选中 subagent thread。
