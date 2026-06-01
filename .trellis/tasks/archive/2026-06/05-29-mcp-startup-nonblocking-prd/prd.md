# MCP startup non-blocking interaction PRD

## Goal

Make MCP server startup a background readiness process instead of a global TUI "task in progress" blocker. Users should be able to resume sessions, run local slash commands, and start ordinary turns while slow MCP servers continue initializing. The feature must preserve clear status visibility and avoid misleading the model into relying on MCP tools that are not ready yet.

## Problem

Current startup UX treats MCP initialization as part of the bottom-pane task-running state. When a slow MCP server is still booting, commands such as `/resume` are rejected with:

```text
'/resume' is disabled while a task is in progress.
```

This is confusing because no agent turn is actually running. In the screenshot-driven case, the UI is blocked by `Starting MCP servers (10/11): computer-use`, not by model work.

The same class of stall can also affect spawned sub-agents. A parent session may be waiting for a spawned agent while the child session starts its own MCP servers, and the visible status can remain on a slow server such as `confluence-mcp` for several minutes. The fix must therefore cover both the main interactive session and sub-agent sessions that construct their own tool routers.

## What I already know

- The TUI derives the bottom-pane "task running" flag from both `agent_turn_running` and `mcp_startup_status.is_some()` in `codex-rs/tui/src/chatwidget/turn_runtime.rs`.
- Slash commands are rejected when `!cmd.available_during_task()` and `bottom_pane.is_task_running()` in `codex-rs/tui/src/chatwidget/slash_dispatch.rs`.
- `/resume`, `/model`, `/clear`, `/permissions`, and several other local commands currently return `false` from `SlashCommand::available_during_task()`.
- MCP startup state is already modeled separately in `ChatWidget` as `mcp_startup_status`, with per-server `Starting`, `Ready`, `Failed`, and `Cancelled` states.
- `McpConnectionManager::new()` already returns a manager quickly and spawns completion reporting through `McpStartupUpdate` and `McpStartupComplete`.
- First-turn tool construction still calls `McpConnectionManager::list_all_tools().await`. If a server has no startup snapshot/cache, listing tools can still wait for that server's client startup.
- `AsyncManagedClient::listed_tools()` can return startup snapshot tools while a server is initializing, and falls back to a snapshot if startup fails.
- Existing required MCP server handling still waits for required servers during session initialization and reports startup failures.
- Spawned agents can initialize MCP independently from the parent session, so main-session-only UI changes are not sufficient.
- This work is being developed in Ralph's private local Codex build based on the `rust-v0.135.0` release line. Do not pull from a feature/main branch with unrelated in-flight product changes.
- The local npm-installed `codex` command may be symlinked to the debug binary during validation. Treat this as intentional for private-build acceptance testing.
- For this private build, update UX is intentionally disabled: no proactive update prompt, and manual `codex update` should not perform an update. Future updates are local merges plus conflict resolution plus local rebuild.
- Validation is staged: build a debug binary first and let Ralph inspect behavior; do not run the broader test/release workflow until he accepts the debug behavior.
- Do not "fix" startup or resume failures by deleting user/project config. Config must remain intact; the code should handle errors or avoid unsafe reloads.

## Resume Regression Findings

During this task, a separate `/resume` regression was reproduced in:

```text
/Users/ralph/Coding/qunhe/maas-platform-merge-test
```

Observed behavior:

- `codex resume --last` could enter a session, but the rendered history was incomplete.
- Starting `codex`, opening `/resume`, and selecting the latest session crashed after selection.
- The crash was not caused by typing `/resume`; it happened after accepting a picker row.
- stderr showed:

```text
thread 'main' (...) has overflowed its stack
fatal runtime error: stack overflow, aborting
```

Debugging showed the existing-session resume path reached cwd resolution and then overflowed before `thread/resume`. The failure was triggered by rebuilding the full config for a same-cwd resume inside an already-running TUI. The safe boundary is:

- same cwd resume: reuse the current in-memory config, carrying service tier and runtime permission policy;
- different cwd resume: rebuild config for the target cwd and surface rebuild errors in the UI;
- picker/page/cwd errors: show an inline/chat error and continue the TUI instead of aborting the process.

The incomplete-history symptom was addressed by reading the resumed thread again after `thread/resume`:

- call `thread/read(includeTurns=true)` after resume;
- if `thread/read` returns more turns than the resume response, use that fuller history for the attached ChatWidget;
- if the read fails, keep the resume response and log/debug the fallback instead of failing resume.

This matters for the MCP startup task because `/resume` is one of the primary local commands that must remain usable while background MCP startup is still active.

## Requirements

### User Interaction

- MCP startup must not, by itself, make the TUI behave as though an agent task is running.
- `/resume` must be usable while MCP servers are still starting, as long as no agent turn is running.
- Local slash commands that are only unsafe during an agent turn should be gated on agent-turn state, not MCP-startup state.
- The startup status header should remain visible while MCP startup is in progress.
- Interrupt hints and "task running" affordances should represent actual agent work, not background MCP startup.
- Queued user input should not be held solely because MCP startup is in progress.
- Existing-session `/resume` must not crash the TUI if picker paging, cwd resolution, or config rebuild fails. These failures should become user-visible messages and return to the active session.
- Same-cwd `/resume` should not rebuild the entire config from disk inside the running TUI. Reusing current in-memory config avoids recursive/stack-heavy config/plugin reload paths and preserves the current runtime policy.

### Tool Availability Semantics

- A new turn may start before all MCP servers are ready.
- The model must only receive MCP tools that are currently available or safely backed by a startup snapshot/cache.
- MCP tools from servers that are still starting and have no snapshot/cache should be omitted from the current turn.
- Once a delayed MCP server becomes ready, its tools should become available to later turns without requiring a full TUI restart.
- If the user requests a tool from a still-starting MCP server, the UX should make the limitation understandable instead of presenting a generic task-running rejection.
- The same nonblocking optional-MCP behavior must apply when constructing tools for spawned sub-agent turns.

### Required MCP Servers

- Existing required-server semantics must remain strict.
- If a server is configured as required, startup failure must still prevent unsafe continuation according to the existing required MCP behavior.
- This PRD does not weaken required MCP guarantees.

### Failure and Completion

- Startup failures should continue to surface as warnings, including the affected server names.
- A failed optional MCP server should not lock the TUI after failure is reported.
- Cancellation during refresh or shutdown should not leave the UI permanently in a startup-running state.
- Debug builds may show more transient WebSocket retry detail than release builds. This is acceptable during local debugging, but retry visibility should not be confused with the root cause of `/resume` crashes.

### Private Build UX Constraints

- Do not show proactive update prompts in Ralph's private build.
- `codex update` must not update the private build; it should be disabled or clearly report that local merge/rebuild is required.
- Hook completion output should render as a compact summary by default. Details belong behind transcript/expand affordances.
- MCP tool output should render at most three visible lines by default. Full output must remain accessible via expansion/transcript.
- Build/debug iteration should compile debug binaries first. Run tests and release builds only after Ralph accepts the visible behavior.

## Acceptance Criteria

- [ ] Starting the TUI with a slow optional MCP server still shows MCP startup progress, but `/resume` no longer emits "disabled while a task is in progress" solely because of MCP startup.
- [ ] Slash-command gating distinguishes agent-turn-running from MCP-startup-running.
- [ ] Submitting a normal prompt while optional MCP startup is in progress can start the turn without waiting for every optional MCP server.
- [ ] A spawned sub-agent can begin a turn without waiting for every optional MCP server that is still starting.
- [ ] The first model request includes ready MCP tools and cached/snapshot tools where available, but omits unavailable non-required MCP tools.
- [ ] Delayed MCP tools are available in a later turn after startup completes.
- [ ] Required MCP server failures still block or fail according to current required-server behavior.
- [ ] TUI tests cover `/resume` or equivalent local command behavior during MCP startup.
- [ ] Core tests cover nonblocking MCP tool-list behavior for an initializing optional server without a snapshot.
- [ ] Existing MCP startup warning/status behavior remains covered.
- [ ] Existing-session `/resume` can select the latest same-cwd session without stack overflow or process abort.
- [ ] Resumed sessions use fuller `thread/read(includeTurns=true)` history when it contains more turns than the initial resume response.
- [ ] Same-cwd resume preserves the active service tier and runtime permission policy while avoiding full config rebuild.
- [ ] Picker/page/cwd failures are rendered as recoverable UI errors rather than terminating the TUI.

## Non-Goals

- Do not hide MCP startup status.
- Do not dynamically inject newly ready MCP tools into an already-sent model request.
- Do not retry or restart failed MCP servers as part of this task.
- Do not redesign MCP configuration, OAuth, or required-server semantics.
- Do not change sandbox environment variable behavior.
- Do not remove or rewrite Ralph's local/project config as part of debugging.
- Do not convert debug acceptance builds into release builds before Ralph has inspected the behavior.

## Suggested Implementation Direction

1. Split UI running semantics.
   - Keep `agent_turn_running` as the source of truth for "task in progress" command gating.
   - Keep `mcp_startup_status` as a separate background readiness indicator.
   - Avoid using `bottom_pane.is_task_running()` as a proxy for slash-command safety where the real condition is agent-turn activity.

2. Preserve background startup display.
   - Keep the MCP startup header and warnings.
   - Ensure startup completion still calls the existing cleanup path for status state and redraw.

3. Add nonblocking MCP tool listing.
   - Prefer a manager method that returns only ready or snapshot-backed tools without awaiting every optional server.
   - Keep the existing blocking path for contexts that truly need it, such as required startup checks or explicit resource reads.

4. Make turn construction use the nonblocking path for optional MCP tools.
   - `built_tools()` should avoid waiting for optional servers that are still initializing.
   - Required-server validation should remain outside this relaxed path.

5. Add focused regression coverage.
   - TUI snapshot or unit coverage for slash-command availability while MCP startup is active.
   - Core/session coverage for a slow optional MCP server not blocking tool router construction.

6. Harden resume switching as a local-command workflow.
   - Treat `/resume` picker failures as recoverable UI state.
   - Resolve cwd before switching sessions, but do not abort the process on resolution errors.
   - Skip config rebuild for same-cwd resume and use the current in-memory config instead.
   - After `thread/resume`, call `thread/read(includeTurns=true)` and prefer the fuller history when available.

## UX Notes

Expected startup experience:

```text
Starting MCP servers (10/11): computer-use
```

Users can still run:

```text
/resume
/model
/status
```

When a turn starts before all optional MCP servers are ready, the model only sees tools that are ready or cache-backed. Delayed tools become visible on later turns after their servers report ready.

## Technical Notes

- Relevant TUI files:
  - `codex-rs/tui/src/chatwidget/turn_runtime.rs`
  - `codex-rs/tui/src/chatwidget/mcp_startup.rs`
  - `codex-rs/tui/src/chatwidget/slash_dispatch.rs`
  - `codex-rs/tui/src/slash_command.rs`
  - `codex-rs/tui/src/resume_picker.rs`
  - `codex-rs/tui/src/session_resume.rs`
  - `codex-rs/tui/src/app/session_lifecycle.rs`
  - `codex-rs/tui/src/app/config_persistence.rs`
  - `codex-rs/tui/src/app_server_session.rs`
- Relevant MCP/core files:
  - `codex-rs/codex-mcp/src/connection_manager.rs`
  - `codex-rs/codex-mcp/src/rmcp_client.rs`
  - `codex-rs/core/src/session/session.rs`
  - `codex-rs/core/src/session/turn.rs`
  - `codex-rs/core/src/session/mcp.rs`
- This task crosses UI state, session startup, and tool-router construction, so use the cross-layer thinking guide before implementation.
- Multi-agent/spawned-agent paths are in scope because they construct turns through the same or similar MCP tool-router path and can surface the same slow optional-server stall.
- There are many existing dirty files in the worktree. Implementation should avoid reverting or bundling unrelated changes.
- Useful local debugging command shape:

```bash
TERM=xterm-256color \
RUST_LOG=codex_tui=trace,codex_app_server=trace \
/Users/ralph/Coding/shenty/codex/codex-rs/target/debug/codex \
  -c log_dir=/tmp/codex-resume-debug-log
```

- Do not redirect stderr for interactive TUI repros unless stderr remains a TTY. Redirecting stderr can make the TUI refuse to start with `TERM is set to "dumb"` / `stderr is not a TTY`.

## Open Questions

- Should ordinary prompt submission proceed immediately even if the user-visible request clearly names a still-starting MCP server, or should the TUI/tool-search layer present a targeted "tool still starting" message first?
- Should private-build-only behavior such as disabled updates be guarded with a local feature/build flag, or remain patched directly in Ralph's private branch?

## Recommended MVP

Allow all slash commands that are currently blocked only by MCP startup to proceed when no agent turn is running, and make optional MCP tool listing nonblocking for turn construction. Keep delayed MCP tools available only on later turns. Do not attempt same-turn dynamic injection.

The first iteration should not special-case `/resume`; `/model`, `/permissions`, `/clear`, and other local commands that are unsafe during an agent turn should be allowed during background MCP startup when no agent turn is active. This keeps the rule aligned with the real hazard: concurrent agent-turn mutation, not background MCP readiness.

Resume hardening can ship as an independent regression fix before the broader MCP nonblocking work because it protects an existing local command path and reduces process-abort risk without weakening required MCP semantics.
