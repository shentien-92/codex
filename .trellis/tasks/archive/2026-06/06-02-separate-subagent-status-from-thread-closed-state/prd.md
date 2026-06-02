# PRD: 回滚 subagent 状态/导航改动，仅保留 total 计数

## 背景

Ralph 确认 statusline 只需要展示当前有几个 subagent。之前为了区分 running/done，把
`<subagent_notification>` 同步进 `agent_navigation`，并把 completed 映射为 closed，这可能
影响继续和 subagent 对话等既有能力。

## 目标

- 回滚会影响 agent navigation、thread closed/liveness、快捷键切换的数据同步改动。
- 保留低风险的 statusline payload `agents.total` 能力。
- 自定义 `~/.codex/statusline.js` 只显示 `agents total N`，不显示 running/done/current name。

## 非目标

- 不改变 `/agent` picker 行为。
- 不改变 subagent 继续对话能力。
- 不再根据 `<subagent_notification>` 推断 running/done 状态。

## 验收标准

- `AppEvent` 不再有 subagent notification 同步事件。
- `<subagent_notification>` 只更新 ChatWidget 内的 statusline agents payload。
- `AgentNavigationState::upsert` 不改变原有 reopen/closed 行为。
- 本地 statusline 输出形如 `agents total 1`。
