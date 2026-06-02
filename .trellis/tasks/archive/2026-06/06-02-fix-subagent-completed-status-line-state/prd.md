# PRD: 修复 subagent completed 后 status line 仍显示 running

## 背景

Ralph 实测收到 `<subagent_notification>` completed 通知后，status line 仍显示
`agents total 1 : running 1`。这说明自定义 statusline 脚本拿到的 payload 仍是
`status: running`。

## 问题判断

`<subagent_notification>` 会先在 ChatWidget 中更新 status line item 为 completed，再通过
AppEvent 同步到 `agent_navigation`。随后 `sync_active_agent_label()` 会从
`agent_navigation.status_line_agents()` 重建 payload。如果 `agent_navigation` 里的同一
thread 仍处于 open/running，completed 状态会被覆盖回 running。

## 目标

- completed/terminal 状态不能被后续 open/running upsert 覆盖。
- completed 通知后 `status_line_agents()` 对应 item 应输出 `completed`。
- 保留 agent navigation 中已完成 agent 的可切换/可查看能力。

## 非目标

- 不改变快捷键。
- 不改变 status line payload schema。
- 不隐藏 completed agent。

## 验收标准

- 若同一 agent 先 running 后 completed，再收到 running/upsert，最终仍是 completed。
- statusline 脚本会显示 `agents total 1 : done 1`。
