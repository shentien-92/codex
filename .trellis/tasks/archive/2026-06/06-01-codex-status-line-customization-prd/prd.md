# Codex Status Line 自定义

## 目标

让 Codex TUI 的 status line 不再局限于当前的内建单行 item 列表。MVP 做“命令驱动的整条 status line 替代来源”：当配置 command source 时，由命令 stdout 负责渲染整块 status 内容，stdout 可以是一行或多行；未配置 command source 时，现有内建 item-list 行为保持不变。

## 已知事实

* Codex 目前已经支持 `[tui].status_line = [...]`，它是一个内建 item id 的有序列表，并通过 `[tui].status_line_use_colors` 控制是否使用主题色。
* 当前渲染路径把 status line 存成并渲染成一个 `ratatui::text::Line`，所以现有数据模型不支持多行。
* 当前仓库里没有 `statusLine.command` 或 `[tui].status_line_command` 这种命令式自定义入口。
* Claude Code 支持 `statusLine` command：命令从 stdin 接收 JSON，上屏 stdout，支持多行、ANSI 颜色、OSC 8 链接、debounce、取消执行和可选定时刷新。
* 社区曾经有一个关闭的 PR：`openai/codex#10170`，实现过单行 command-backed status line。它很有参考价值，但不能直接复用，因为它早于现在的内建 item-list status line 架构。

## 需求

* 保持现有内建 `[tui].status_line = [...]` 行为和配置兼容性。
* 支持 status line 内容包含多行渲染结果。
* 新增一个可选的脚本/命令 status line 来源，MVP 中它替代整条 status line，不作为 `[tui].status_line = [...]` 数组里的混排 item：
  * 本地执行，不消耗模型/API。
  * `command` 使用 argv 数组形式，不隐式通过 shell 解释。
  * 通过 stdin 接收稳定 JSON payload。
  * 将 stdout 渲染为 status line 行。
  * MVP 必须支持纯文本多行和 ANSI SGR 样式；OSC 8 hyperlink 不纳入 MVP。
  * 有硬编码 timeout 和 cancellation，不能阻塞 TUI 输入或 turn 推进；MVP 不暴露 timeout 配置。
  * 在相关状态变化时刷新，并做 debounce；不允许从 render path 直接执行 command。
  * 支持可选固定刷新间隔，用于时钟、git、外部状态等场景。
  * 默认最多渲染 3 行，允许用户配置 `max_lines`，但实现必须有硬上限，建议硬上限 5 行。
* 命令输出为空、失败、超时时不能破坏 footer；如果已有上一次成功输出，则继续保留上一次成功输出；如果从未成功过，则显示为空。错误只进入日志，并最多发一次非阻塞 warning。
* Shell 执行必须和 Codex 已有的用户配置命令执行安全/信任模型保持一致：status line command 是需要 trust gate 的本地命令执行面，未 trusted 时不执行。
* 增加测试和 snapshot，覆盖 footer 高度、多行渲染、截断、命令失败/超时、配置解析。

## 验收标准

* [ ] 如果没有设置新的 command 配置，已有 `[tui].status_line` item-list 配置保持原样渲染。
* [ ] 配置 status-line command 后，命令输出一行时能替代整条内建 status line。
* [ ] 配置 status-line command 后，命令输出两行或更多行时，footer 能正确预留高度，不和 composer 文本或右侧上下文重叠。
* [ ] 未配置 `max_lines` 时最多渲染 3 行；配置超过硬上限时被 clamp 到硬上限，并且有测试覆盖。
* [ ] 命令执行是异步的，有 debounce、硬编码 500ms timeout，并且新刷新请求到来时能取消/重启旧执行。
* [ ] 刷新模型是事件触发为主、可选 `refresh_interval_ms` 为辅；所有触发进入同一个 debounced runner，最小执行间隔 300ms。
* [ ] 命令 stdin 至少包含：model、cwd/current dir、project/root dir、permissions/approval mode、run status、context usage、token usage、session/thread id、thread title、可用时的 git branch/PR 信息、Codex version、terminal dimensions。
* [ ] JSON payload 使用 Codex-native typed schema，不承诺 Claude Code schema 兼容；字段必须诚实反映 Codex 真实状态。
* [ ] 命令 stdout 支持纯文本多行和 ANSI SGR 样式，至少覆盖已有 parser 能处理的颜色/基础样式。
* [ ] 未 trusted workspace / config layer 下不执行 status line command，并有一次性 warning 或等价可见提示；不能静默执行。
* [ ] command config 存在但未 trusted 时 fallback 到现有内建 item-list status line；trusted command 运行失败时不 fallback 到内建 item-list，按 command 失败语义处理。
* [ ] 命令失败、超时、空 stdout 都有测试覆盖：已有成功输出时保留上一次成功输出；从未成功时显示为空；不会留下半截脏输出。
* [ ] TUI snapshot 能让多行视觉行为可审查。
* [ ] 如果改动 config 类型，必须重新生成 config schema。

## 技术方案

推荐路径：

1. 引入一个小的 status line 内容模型，例如 `StatusLineContent { lines: Vec<Line<'static>>, hyperlink: ... }`，替换 footer 边界上的 `Option<Line<'static>>`。
2. 更新 footer 高度和布局逻辑，让 passive status content 可以占用 N 行；MVP 建议保守上限为 3 行。
3. 保留内建 item-list 渲染：把现有 segments 转成单行 `StatusLineContent`。
4. 新增 command-backed source：把 JSON 输入喂给 shell command，捕获 stdout/stderr/exit status，并返回规范化后的 status 内容。MVP 不支持 command item 与内建 item 混排；command source 存在时，它负责整块 status content。
5. 从 `refresh_status_surfaces` 和其他现有 status refresh 点触发命令刷新，但实际进程执行必须离开 render path。MVP 触发点包括：TUI 初始化后、model/reasoning/service tier 变化、cwd/thread/session 状态变化、run state 变化、token/context/rate-limit 更新、git branch/PR summary 异步返回、terminal resize，以及可选 `refresh_interval_ms`。
6. 定义 Codex-native typed Rust payload struct，并用 serde 序列化。不要手写 ad hoc JSON；之前社区 PR 已经被 reviewer 指出这个问题。不做 Claude Code schema 兼容，只参考其交互模式。
7. 输出解析应复用已有 ANSI 解析能力（例如 `codex_ansi_escape`）来支持 ANSI SGR。MVP 不改造 footer hyperlink 模型，因此不承诺 OSC 8。
8. 执行前必须做 trust gate。优先复用或贴近 hooks 的 trusted config layer / workspace trust 判断，避免在 TUI 中裸跑任意配置命令。
9. Runner 状态机应区分 `latest_successful_content`、`in_flight`、`pending_refresh` 和一次性 warning 标记。失败/超时不清空 `latest_successful_content`。
10. 以向后兼容的方式增加配置。候选 TOML：

```toml
[tui.status_line_command]
command = ["/Users/me/.codex/statusline.py", "--style", "compact"]
refresh_interval_ms = 1000
max_lines = 3
```

Timeout 在 MVP 中硬编码为 500ms，不暴露配置项。之前社区 PR 的 reviewer 明确反对增加不必要的 config knob。后续如果真实用户脚本普遍需要更长时间，再考虑配置化。

`max_lines` 默认值为 3；实现层设置硬上限，建议为 5。超过上限的脚本输出应被截断或忽略多余行，不能挤占 composer 的基本输入空间。

`command` 使用 argv 数组，不隐式走 shell。需要 shell 能力时，用户可以显式写成 `["/bin/sh", "-lc", "..."]` 或平台等价形式。

刷新策略：事件触发为主，可选 interval 为辅；所有触发进入同一个 debounced runner，最小执行间隔 300ms。禁止在 `render()` 或等价绘制路径中直接执行 command。

执行约束：

* `STATUS_LINE_COMMAND_TIMEOUT = 500ms`
* `MIN_STATUS_LINE_COMMAND_INTERVAL = 300ms`
* 超时必须 kill child，并按失败语义保留上一次成功输出。
* 超时 warning 最多发一次，提示用户优化脚本。

Fallback 矩阵：

* command config 不存在：使用现有内建 `[tui].status_line = [...]` item-list。
* command config 存在且 trusted：使用 command output 替代整条 status line。
* command config 存在但 untrusted：不执行 command，fallback 到内建 item-list，并发一次 warning。
* command config trusted 但运行失败/超时/空输出：不 fallback 到内建 item-list；已有上次成功 command output 时保留，否则 command content 为空。

Payload schema 采用 Codex 独立模型。示例方向：

```json
{
  "model": { "id": "...", "displayName": "...", "reasoningEffort": "high" },
  "workspace": { "cwd": "...", "currentDir": "...", "projectDir": "..." },
  "session": { "id": "...", "threadTitle": "...", "codexVersion": "..." },
  "status": { "runState": "...", "permissions": "...", "approvalMode": "..." },
  "context": { "windowTokens": 0, "usedTokens": 0, "usedPercent": 0, "remainingPercent": 100 },
  "usage": { "inputTokens": 0, "outputTokens": 0, "totalTokens": 0 },
  "git": { "branch": "...", "prNumber": 123, "prUrl": "..." },
  "terminal": { "columns": 120, "lines": 40 }
}
```

11. `/statusline` 设置 UI 是否也支持配置 command 可以后置。第一版只支持手写 config；现有 `/statusline` setup UI 继续只管理内建 item-list。
12. 为脚本作者和 AI 生成脚本场景提供清晰 payload 示例。MVP 不内置 TUI 预览编辑器，也不新增 `codex statusline --dry-run` 之类的 CLI；脚本可以通过文档里的 sample JSON 或真实运行后的 stdout 预览。

## 决策（ADR-lite）

背景：Codex 已经有有用的内建 status line，但它受限于单行和固定 item id。Claude Code 的脚本模型更灵活，也天然覆盖多行展示。

决策：先把 footer status content 抽象成支持多行的模型，再把 command 作为可选的整条 status line 替代来源接入。现有 item-list config 继续作为默认和兼容路径；不在 MVP 中支持 command item 与内建 item 混排。

影响：这个改动会同时触及 TUI layout 和 config/runtime execution，比简单“允许字符串里带换行”要大；但它能一次性得到目标交互模型，避免先做单行脚本、马上又为多行重构。选择“整条替代”会牺牲第一版的组合灵活性，但显著降低配置歧义、调度复杂度和布局测试面。选择默认 3 行能覆盖常见 dashboard 场景；硬上限避免脚本输出无限挤压输入区。失败时保留上一次成功输出能降低 footer 抖动，但也意味着外部状态可能短暂变旧，需要通过日志和一次性 warning 暴露故障。

## 不做范围

* 不做从自然语言 `/statusline` prompt 自动生成脚本。
* 不做 Claude Code 风格的 `subagentStatusLine` 行级自定义。
* 不替换现有内建 item selector UI。
* MVP 不改造 `/statusline` setup UI 来编辑 command 配置、argv 数组或预览脚本输出。
* MVP 不新增 status-line dry-run CLI。
* MVP 不支持在 `[tui].status_line = [...]` 中混排 command item 与内建 item。
* OSC 8 hyperlink 不纳入 MVP；后续如果要支持，需要重新设计多行 footer 的链接模型。
* status-line runner 内部不做网络请求或模型调用。
* MVP 不提供 shell string 配置，不隐式处理 shell quoting/expansion。
* 不绕过 workspace/config trust 机制执行 status-line command。
* 不承诺 Claude Code payload schema 兼容，不伪造 Codex 没有或语义不同的字段。
* 不在 TUI render path 中执行或 await status-line command。
* MVP 不暴露 timeout 配置项。

## 调研引用

* [`research/codex-status-line-current-state.md`](research/codex-status-line-current-state.md) - Codex 现状是内建单行 status-line items，没有脚本 runner，也没有多行数据路径。
* [`research/claude-code-statusline-pattern.md`](research/claude-code-statusline-pattern.md) - Claude Code 使用 JSON stdin + stdout 渲染行的 command 模型，多行是一等能力。
* [`research/codex-community-prior-art.md`](research/codex-community-prior-art.md) - `openai/codex#10170` 已经实现过 command runner；应借鉴设计，不应直接 cherry-pick。

## 技术备注

* 主要检查过的本地文件：`codex-rs/tui/src/chatwidget/status_surfaces.rs`、`codex-rs/tui/src/bottom_pane/footer.rs`、`codex-rs/tui/src/bottom_pane/chat_composer.rs`、`codex-rs/tui/src/bottom_pane/chat_composer/footer_state.rs`、`codex-rs/tui/src/bottom_pane/status_line_style.rs`、`codex-rs/config/src/types.rs`、`codex-rs/core/src/config/mod.rs`、`codex-rs/core/src/config/edit.rs`。
* 现有 hook command config（`codex-rs/config/src/hook_config.rs`）可以作为 command/timeout/status-message 形状参考，但 status-line command 需要自己的渲染输出契约。
* 之前社区 PR 暴露出的坑要避免：复用 `[tui].status_line` 导致配置歧义、手写 raw JSON payload、非 UTF-8 path panic、stdin 没有 shutdown、命令执行不 throttle、payload 字段和 `/status` 语义漂移。
* 输出格式决策：MVP 支持纯文本多行和 ANSI SGR；OSC 8 hyperlink 后置。
* 命令配置决策：MVP 使用 argv 数组，不隐式通过 shell 执行。需要 shell 时由用户显式配置 shell 程序。
* 安全决策：status line command 是本地命令执行面，必须走 trust gate；未 trusted 时不执行。
* Payload 决策：使用 Codex-native typed schema；参考 Claude Code 的 stdin JSON 模式，但不做字段兼容承诺。
* 刷新决策：事件驱动为主，可选 interval 为辅；统一 debounced runner，最小执行间隔 300ms，render path 无副作用。
* Fallback 决策：untrusted command fallback 到内建 item-list；trusted command 自身失败时不 fallback，避免 footer 在 command/内建之间跳变。
* Timeout 决策：MVP 硬编码 500ms，不暴露配置；超时 kill child 并保留上一次成功输出。
* UI 决策：MVP 不改 `/statusline` setup UI；脚本创建和预览依赖清晰的 config/payload 契约，AI 可以基于该契约生成脚本和预览输出。
* 调试决策：MVP 只提供 sample payload，不新增 dry-run CLI；真实 dry-run 能力后续按用户需求评估。
* 所有用户可见 UI 改动都必须在 `codex-rs/tui` 里增加或更新 `insta` snapshot 覆盖。
