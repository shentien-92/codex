# PRD: 精简 agent status line 文案

## 背景

Ralph 确认 agent 快捷键可用，但底部 status line 太长。当前显示包含 agent 名字和
切换提示，占用空间且信息重复。

## 目标

- 自定义 status line 的 agent 段显示为：
  `agents total 1 : running 1`
- 多状态时显示：
  `agents total 3 : running 1 / pending 1 / done 1`
- 去掉当前 agent 名字。
- 去掉刚加的内置 footer 切换提示。

## 非目标

- 不改变快捷键行为。
- 不改变 status line payload 结构。
- 不改变 agent navigation 行为。

## 验收标准

- `~/.codex/statusline.js` 使用确认后的 agent 文案。
- 内置 footer active agent label 不再追加快捷键提示。
