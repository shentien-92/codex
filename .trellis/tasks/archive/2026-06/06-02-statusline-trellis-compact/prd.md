# 精简 Codex statusline Trellis 状态

## Goal

精简当前 Codex 自定义 statusline 中 Trellis 状态段的信息密度，只调整 Trellis status 相关展示，让它更像任务状态摘要，而不是把 task dir、assignee、priority、status 全量拼在一行。

## What I Already Know

- 当前 Codex 实际使用 `/Users/ralph/.codex/statusline.js`，配置在 `/Users/ralph/.codex/config.toml` 的 `[tui.status_line_command]`。
- 当前 repo 内也有 `.codex/statusline.js`，内容与全局脚本相近，但实际生效的是全局脚本。
- 用户明确要求“不用照抄 Claude，只改 Trellis status 相关”。
- 当前 Trellis 段由 `trellisSegment()` 生成，展示为：`status · priority · assignee · task-dir`。
- 当前无 Trellis active task 时，Trellis 段为空，只展示 branch。

## Requirements

- 只改 Trellis status 展示相关逻辑。
- 保留现有 model、permissions、runState、ctx、currentDir、branch 展示结构。
- Trellis 有当前任务时，展示应更短、更偏任务状态摘要。
- 避免展示低价值的 task directory slug。
- 保留 assignee/creator 作为 user 信息。
- 保留 Trellis active task 总数，语义与 `task.py list` 一致：`.trellis/tasks/` 下未归档且有 `task.json` 的任务目录。
- 保持脚本快速、无额外依赖、容错读取 Trellis 文件。

## Acceptance Criteria

- [ ] 有 Trellis 当前任务时，Trellis 段显示 `{priority} {title} ({status}) · {user} · {task_count} task(s)` 风格的短摘要。
- [ ] `{task_count}` 统计 `.trellis/tasks/` 下未归档且有 `task.json` 的 task，和 Claude statusline / `task.py list` 的 active task 语义一致。
- [ ] 任务标题过长时会截断，不挤爆 statusline。
- [ ] 无 Trellis 当前任务时行为不变，不额外显示 Trellis 空信息。
- [ ] 现有非 Trellis statusline 字段不改变。
- [ ] 能通过模拟 payload 预览输出。

## Out of Scope

- 不重写整体 statusline 布局。
- 不改权限提示、模型、ctx 进度条、branch 的展示逻辑。
- 不改 Claude Code statusline。
- 不改 Codex Rust TUI 内建 status line。

## Technical Notes

- 主要文件：`/Users/ralph/.codex/statusline.js`
- 可选同步文件：repo 内 `.codex/statusline.js`，用于保持项目配置副本一致。
- 当前脚本通过 `.trellis/.runtime/sessions/*.json` 找当前 task，再读 `task.json`。
