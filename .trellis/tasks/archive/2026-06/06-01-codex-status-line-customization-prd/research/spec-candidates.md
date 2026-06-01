# Spec / ADR Candidates

## ADR candidate: command-backed status line replaces the whole status content in MVP

Decision crystallized during grilling: MVP should treat `status_line_command` as an alternative source for the entire status line, not as a command item mixed into `[tui].status_line = [...]`.

Why it may deserve an ADR later:

- Harder to reverse once config is released, because item-level command config and whole-line command config imply different TOML shapes.
- Surprising without context, because users familiar with existing `[tui].status_line = [...]` may expect `{ type = "command" }` to appear inside that array.
- Real trade-off: whole-line replacement preserves compatibility and reduces layout/scheduling complexity; mixed items are more flexible but create typed-union config, multi-command scheduling, and per-item failure semantics.

Do not promote automatically. Revisit during finish after implementation details settle.

## Spec candidate: status-line command row limits

Decision crystallized during grilling: command-backed status line output defaults to 3 rendered rows, exposes `max_lines`, and clamps to a hard implementation cap, suggested at 5 rows.

Why it may deserve spec treatment:

- This is a user-visible TUI contract and should stay stable after release.
- It protects the composer from being displaced by unbounded script output.
- It is probably not ADR-worthy by itself unless the implementation reveals a deeper layout trade-off.

## Spec candidate: status-line command failure semantics

Decision crystallized during grilling: command-backed status line failures, timeouts, and empty stdout keep the latest successful content when one exists; if no successful content exists yet, the rendered command-backed status content is empty. Errors are logged and may emit at most one non-blocking warning, but they do not render persistent error text in the footer.

Why it may deserve spec treatment:

- It is user-visible behavior that prevents footer flicker and avoids turning ambient UI into an error banner.
- It defines how much stale status information is acceptable.
- It is likely a spec note rather than ADR unless implementation trade-offs make it hard to reverse.

## Spec candidate: status-line command output format

Decision crystallized during grilling: MVP supports plain-text multi-line stdout plus ANSI SGR styling. OSC 8 hyperlinks are explicitly deferred because the current footer hyperlink model is single-target and PR-number oriented.

Why it may deserve spec treatment:

- It sets user expectations for what scripts can emit.
- It preserves the highest-value customization request, colors, without expanding the first implementation into a multi-line hyperlink model.
- It is probably not ADR-worthy unless the ANSI parser choice creates lasting constraints.

## Spec candidate: status-line command configuration shape

Decision crystallized during grilling: MVP uses argv-array command configuration and does not implicitly execute through a shell. Users who need shell behavior can explicitly configure `["/bin/sh", "-lc", "..."]` or a platform equivalent.

Why it may deserve spec treatment:

- It is a config contract that affects quoting, escaping, and security expectations.
- It aligns with Rust process execution and the prior community PR's argv shape.
- It avoids shell-string ambiguity in the first release.

Why it may deserve an ADR later:

- If released publicly, changing from argv-only to string/union later is a compatibility concern.
- Future readers may wonder why Codex differs from Claude Code's string command shape.

## ADR candidate: status-line command execution requires trust

Decision crystallized during grilling: status-line commands are treated as local command execution and must pass the existing workspace/config trust model before execution. Untrusted contexts do not execute the command and should surface a one-time warning or equivalent visible hint.

Why it may deserve an ADR later:

- Hard to reverse safely after release because users may rely on when commands do or do not run.
- Surprising without context because a status line looks like passive UI, but the command can read files/environment and run arbitrary local code.
- Real trade-off: requiring trust protects users and aligns with hooks, but it makes first-run setup less seamless than Claude Code-style always-on local status scripts.

## Spec candidate: status-line command payload schema is Codex-native

Decision crystallized during grilling: command stdin uses an independent Codex-native typed schema. Claude Code informs the interaction pattern, but Codex does not promise Claude Code field compatibility.

Why it may deserve spec treatment:

- It defines the contract script authors will depend on.
- It avoids semantically inaccurate compatibility fields such as cost/duration values Codex may not own.
- It should probably live near config/API docs or generated schema rather than as a long-term ADR unless the schema boundary becomes controversial.

## Spec candidate: status-line command refresh model

Decision crystallized during grilling: refreshes are event-driven with an optional timer. All refresh requests pass through one debounced runner with a 300ms minimum execution interval. Command execution is never triggered directly from the render path.

Why it may deserve spec treatment:

- It protects TUI responsiveness and avoids render side effects.
- It defines when script authors should expect their status content to update.
- It mirrors useful Claude Code behavior without tying the implementation to every frame redraw.

## Spec candidate: status-line command fallback matrix

Decision crystallized during grilling: if command config is absent, Codex uses the built-in item-list status line. If command config exists but is blocked by trust, Codex falls back to the built-in item-list and emits one warning. If a trusted command fails, times out, or emits empty output, Codex does not fall back to the built-in item-list; it keeps the last successful command output or renders empty if no success exists.

Why it may deserve spec treatment:

- It avoids footer content jumping between command and built-in modes on transient script failures.
- It preserves safe default UI when command execution is blocked before it starts.
- It is a user-visible behavior matrix worth locking in tests.

## Spec candidate: status-line command timeout policy

Decision crystallized during grilling: MVP hard-codes a 500ms command timeout and does not expose timeout configuration. The runner kills timed-out children, keeps the latest successful output, and emits at most one warning suggesting script optimization.

Why it may deserve spec treatment:

- It protects responsiveness while keeping config surface small.
- It follows reviewer feedback from prior community PR #10170 that timeout config may not be worth exposing initially.
- It can be revisited later if real scripts commonly exceed the fixed timeout.

## Spec candidate: no TUI setup editor for command status line in MVP

Decision crystallized during grilling: MVP does not extend `/statusline` setup UI to create, edit, or preview command-backed status lines. Users configure the command manually; agents or users can generate scripts against the documented payload schema and preview by running the script with sample JSON or through the live TUI.

Why it may deserve spec treatment:

- It keeps MVP focused on the runtime contract rather than a configuration editor.
- It clarifies that `/statusline` remains the built-in item-list setup surface for now.
- It preserves a future path for AI-assisted script generation without adding TUI interaction branches now.

## Spec candidate: no status-line dry-run CLI in MVP

Decision crystallized during grilling: MVP provides a sample payload for script authors and AI-generated scripts, but does not add a new dry-run CLI command such as `codex statusline --dry-run`.

Why it may deserve spec treatment:

- It keeps the public CLI surface smaller for the first release.
- It avoids having to define how dry-run samples live state, cwd, trust, and config layers before the runtime contract is proven.
- It leaves room to add dry-run later if script debugging becomes a common pain point.
