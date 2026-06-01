# Codex Status Line Current State

## Question

Does Codex already support multi-line or script-driven status lines, and where would this feature fit?

## Findings

Codex already has a configurable TUI status line, but it is an internal item-list renderer rather than a user script runner.

Current config shape:

- `[tui].status_line = [...]` is an ordered list of built-in item identifiers.
- `[tui].status_line_use_colors = true|false` controls theme-derived colors.
- When unset, the TUI defaults to `model-with-reasoning` and `current-dir`.
- Empty list is persisted as an explicit "hide the status line" state.

Important files:

- `codex-rs/config/src/types.rs`: `TuiConfigToml.status_line` and `status_line_use_colors`.
- `codex-rs/core/src/config/mod.rs`: resolved config fields `tui_status_line` and `tui_status_line_use_colors`.
- `codex-rs/core/src/config/edit.rs`: persistence helpers for the status-line item list.
- `codex-rs/tui/src/chatwidget/status_surfaces.rs`: parses item ids, collects runtime values, refreshes footer status line and terminal title from one shared state snapshot.
- `codex-rs/tui/src/bottom_pane/status_line_style.rs`: converts built-in segments into a single `ratatui::text::Line`.
- `codex-rs/tui/src/bottom_pane/footer.rs`: treats the configurable status line as a contextual passive footer row.
- `codex-rs/tui/src/bottom_pane/chat_composer/footer_state.rs`: stores `status_line_value: Option<Line<'static>>`.
- `codex-rs/tui/src/bottom_pane/chat_composer.rs`: reserves footer height, truncates the status line to one row, overlays the right-side context when it fits, and marks hyperlinks.

Current support:

- Supported: built-in single-row status line composed from known items such as model, current dir, git branch, PR number, branch changes, status, permissions, context usage, rate limits, Codex version, session id, fast mode, raw output, thread title, and task progress.
- Supported: theme-based color styling for built-in items.
- Supported: one hyperlink target, currently tied to PR-number status-line content.
- Not found: a `[tui].status_line_command` / `statusLine.command` config shape.
- Not found: a custom status-line command runner that receives JSON on stdin.
- Not found: multi-line status-line storage or rendering. The data path uses `Option<Line<'static>>`, `passive_footer_status_line` returns `Option<Line<'static>>`, `render_footer_line` renders one line, and width fallback/truncation assumes a single row.

## Implementation Implications

Adding multi-line output is a TUI layout/data-model change even without scripts:

- `FooterState.status_line_value` and `FooterProps.status_line_value` need to become a collection, likely `Vec<Line<'static>>` wrapped in a small domain type.
- Footer height calculation must account for status-line line count in passive contexts.
- Width truncation should operate per line, preserving the right-side mode/context row only where it still makes sense.
- Hyperlink handling must either remain single-target for PR rows or become span-level/multi-line aware.

Adding script-driven customization is a broader cross-layer feature:

- Config schema needs a command-bearing shape, not just `Vec<String>`.
- Runtime needs a debounced async runner with timeout/cancellation so refreshes do not block TUI input.
- The runner needs a stable JSON input contract assembled from the same state used by `status_surfaces.rs`.
- Output parsing should support plain text, ANSI colors, OSC 8 hyperlinks, empty output fallback, and line-count limits.
- Shell execution should reuse existing command/hook conventions where practical, especially trust and timeout behavior, but status-line rendering should remain a TUI-owned surface.

## Recommendation

Treat "multi-line footer status content" as the rendering foundation, then add a script source that can produce one or more lines. That keeps the data model honest and avoids forcing command output back into a single `Line`.
