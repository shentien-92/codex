# Codex Community Prior Art

## Question

Is there an existing upstream/community PR or issue that already implements command-backed or multi-line Codex status-line customization?

## Sources

- `openai/codex#10170`: https://github.com/openai/codex/pull/10170
- `openai/codex#17827`: https://github.com/openai/codex/issues/17827
- `openai/codex#20043`: https://github.com/openai/codex/issues/20043
- `openai/codex#20140`: https://github.com/openai/codex/issues/20140
- `openai/codex#20244`: https://github.com/openai/codex/issues/20244
- `openai/codex#16921`: https://github.com/openai/codex/issues/16921

## Findings

There is a directly relevant closed community PR:

- `#10170 feat(tui): add custom status line support`
- Author branch: `fcoury/codex`, `feat/status-line`
- Created January 29, 2026; closed February 20, 2026; not merged.
- It implemented an external command runner for the TUI status line.

PR #10170 behavior:

- Configured via `[tui] status_line = ["my-status-script", "--arg"]`.
- Optional timeout config was explored, then reviewers questioned whether this knob should exist.
- Command receives a JSON payload on stdin.
- First stdout line becomes the status-line text.
- ANSI output is parsed with `codex_ansi_escape::ansi_escape_line`.
- Runner uses async process execution, bounded timeout, `kill_on_drop`, explicit stdin shutdown, coalescing while a command is in flight, and a 300ms minimum execution interval.
- On failure, it warns/logs and keeps the last successful output rather than crashing the TUI.
- Added `codex-rs/tui/src/status_line.rs`, app events, TUI wiring, footer layout changes, config schema changes, and snapshot tests.

Useful reviewer feedback on #10170:

- Define a typed Rust payload struct and let serde serialize it instead of building raw `serde_json::Value`.
- Manually verify exposed fields against `/status`; one review caught incorrect used/remaining context percentages.
- Include ChatGPT subscription usage/rate limit information in the payload.
- Consider duration fields similar to Claude Code's `total_duration_ms` / `total_api_duration_ms`.
- Avoid unnecessary config knobs; every knob becomes maintenance and documentation surface.
- Add throttling because frequent command execution can become a TUI performance issue.
- Close/shutdown stdin after writing JSON so child processes waiting for EOF do not hang.
- Convert paths with `to_string_lossy()` or an explicit schema policy to avoid panics on non-UTF8 Unix paths.

Why #10170 is not directly reusable as-is:

- It predates the current built-in `[tui].status_line = [...]` item-list design. Reusing that same config key for argv would now be a breaking ambiguity.
- It renders only the first stdout line, while the new desired scope includes multi-line output.
- It places much of the status payload assembly in `chatwidget.rs`; current local code has since moved status-line and terminal-title logic into `chatwidget/status_surfaces.rs`, so the integration point should be updated.
- It was built before the newer shared status surface model, PR summary items, permissions/approval items, blended token count, and current footer layout.

Open issue consolidation:

- `#17827 Customizable status line` is the active tracking issue. Maintainer guidance in duplicate issues points users to upvote this issue.
- `#20043`, `#20140`, and `#20244` are duplicate/related requests specifically asking for command-backed status lines, ANSI colors, custom progress bars, multi-line layout, external workflow state, and stable JSON stdin.
- `#16921` says the author had a branch/PR ready for custom status-line plugins, but no public PR was discoverable from quick GitHub search.

## Recommendation

Use #10170 as prior art, not as a cherry-pick. The useful pieces are the async runner shape, timeout/kill/stdin-shutdown handling, ANSI parsing precedent, event update path, and reviewer feedback. The new implementation should adapt those ideas to the current `status_surfaces.rs` architecture, use a non-conflicting config shape, support multi-line stdout, and define a typed JSON payload from day one.
