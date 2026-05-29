# WS reconnecting diagnostics PRD

## Goal

Make Responses WebSocket reconnecting diagnosable in Ralph's private Codex build. When the TUI shows `Reconnecting...`, logs should let us determine whether the cause is local network/proxy instability, gateway/server close, websocket handshake failure, stale/reused websocket state, incremental payload reuse, or fallback from WebSocket to HTTPS.

This PRD is about observability first. It should not change retry policy, fallback policy, or user-visible reconnect behavior unless a later fix requires it.

## Problem

In the debug private build, the TUI often shows `Reconnecting...` while older Codex windows using WebSocket do not show the same noise. Release builds intentionally hide the first WebSocket retry, while debug builds show it. That explains why debug is noisier, but it does not explain why retry happens.

We need enough structured logs to answer:

- Did the websocket handshake fail, or did the stream fail after a request was sent?
- Was the connection new, prewarmed, cached, or reused?
- Was the request using full payload or incremental delta payload?
- Did the server close normally, reset, timeout, return an HTTP status, or produce a protocol error?
- Did Codex fall back from WebSocket to HTTPS?
- Is this correlated with a specific turn, model, provider, gateway route, or retry count?

## Current State

Some retry-loop logging already exists in `codex-rs/core/src/responses_retry.rs`:

- `turn_id`
- `retries`
- `max_retries`
- `delay_ms`
- `http_status_code`
- `responses_websocket_enabled`
- `stream_error` for sampling
- `compact_error` for remote compaction

This is useful after a retryable stream error has reached the common retry handler, but it is not enough to locate the root cause. It does not yet show connection creation/reuse, handshake timing, request mode, close frame details, or fallback transitions.

## Requirements

### Logging Scope

- Add structured logs around WebSocket connection lifecycle:
  - prewarm started/skipped/succeeded/failed/timed out;
  - connection requested for a turn;
  - existing connection reused vs discarded;
  - new connection attempt started;
  - handshake succeeded or failed;
  - connection reset/closed/unavailable.
- Add structured logs around request streaming:
  - sampling vs remote compaction;
  - warmup vs normal turn;
  - full request payload vs incremental websocket delta;
  - whether the connection was reused;
  - stream request succeeded, failed, or ended early.
- Add structured logs around fallback:
  - retry exhaustion before fallback;
  - fallback transport selected;
  - WebSocket globally disabled for the session after fallback.
- Preserve current TUI behavior:
  - debug builds may display the first retry;
  - release builds should continue hiding the first transient WebSocket retry unless policy changes separately.

### Correlation Fields

Every WebSocket diagnostic log should include the fields available at that boundary:

- `turn_id`
- `model`
- `provider`
- `request_kind` (`sampling`, `remote_compaction_v2`, `prewarm`)
- `transport` (`responses_websocket`, `https_fallback`)
- `responses_websocket_enabled`
- `connection_reused`
- `warmup`
- `incremental_payload`
- `attempt`
- `duration_ms`
- `timeout_ms`
- `http_status_code`
- `error`

When a field is not available at a boundary, omit it rather than threading broad state through unrelated layers.

### Privacy and Safety

- Do not log auth tokens, cookies, full URLs with sensitive query strings, request bodies, prompts, tool outputs, or raw response payloads.
- If endpoint identity is useful, log a sanitized host/route label rather than the complete URL.
- Keep logs at `debug` or `trace` for high-volume lifecycle events; use `warn` for retry/fallback/failure events.

## Acceptance Criteria

- [ ] A single `Reconnecting...` event can be correlated to one `turn_id` and one retry-loop log entry.
- [ ] Logs show whether the failed stream used WebSocket or HTTPS fallback.
- [ ] Logs show whether the failed stream used a reused WebSocket connection or a newly opened one.
- [ ] Logs show whether the request used a full payload or incremental WebSocket payload.
- [ ] Handshake failures include duration, timeout, sanitized endpoint identity, and error class/detail.
- [ ] Server close/reset/protocol failures include the closest available close/error detail without leaking payload contents.
- [ ] Fallback from WebSocket to HTTPS is logged once with the triggering error and retry count.
- [ ] Debug validation can be run with `RUST_LOG=codex_core=debug,codex_tui=debug` and `-c log_dir=...`.
- [ ] No tests/release build are required before Ralph accepts the debug behavior.

## Non-Goals

- Do not change retry limits, backoff, or fallback behavior in this task.
- Do not suppress debug reconnect UI as a substitute for diagnosing the cause.
- Do not disable WebSockets by default.
- Do not log sensitive request or auth data.
- Do not remove user or project configuration to work around the issue.

## Suggested Implementation Direction

1. Keep the existing retry-loop logs in `responses_retry.rs`.
2. Add connection lifecycle logs in `codex-rs/core/src/client.rs` near:
   - `responses_websocket_enabled`
   - `connect_websocket`
   - `preconnect_websocket`
   - `websocket_connection`
   - `stream_responses_websocket`
   - `try_switch_fallback_transport`
3. Add prewarm-specific logs in `codex-rs/core/src/session_startup_prewarm.rs` only where they clarify prewarm vs turn-time connection behavior.
4. Prefer local structured logging over user-visible warning spam.
5. After adding logs, reproduce in:

```bash
cd /Users/ralph/Coding/qunhe/maas-platform-merge-test

TERM=xterm-256color \
RUST_LOG=codex_core=debug,codex_tui=debug \
/Users/ralph/Coding/shenty/codex/codex-rs/target/debug/codex \
  -c log_dir=/tmp/codex-ws-debug-log
```

6. Inspect:

```bash
rg "websocket|Reconnecting|retrying request|fallback" /tmp/codex-ws-debug-log/codex-tui.log
```

## Diagnostic Decision Tree

- Handshake fails before request send:
  - investigate gateway availability, auth headers, proxy, DNS, TLS, or timeout.
- New connection succeeds, stream fails immediately:
  - investigate gateway/server response handling and request payload compatibility.
- Reused connection fails, new connection succeeds on retry:
  - investigate stale cached connection or server idle timeout.
- Incremental payload fails but full payload succeeds:
  - investigate websocket delta construction or server incremental-state mismatch.
- Prewarm connection fails but turn-time connection succeeds:
  - investigate startup timing only; avoid treating it as a turn failure.
- Retry exhaustion triggers HTTPS fallback:
  - preserve the triggering error and compare behavior against non-WebSocket transport.

## Open Questions

- Should there be a config flag to force full WebSocket payloads for diagnosis, without disabling WebSockets entirely?
- Should the TUI expose a compact "debug details available in log_dir" hint after repeated reconnects?
- Should retry logs include a stable websocket connection id generated locally, so reuse/discard decisions can be followed without logging endpoint details?

## Current Known Patch

As of this PRD, `responses_retry.rs` already has retry-loop fields for `turn_id`, retry counts, delay, HTTP status, WebSocket enabled state, and concrete error text. The remaining work is to add connection/request lifecycle logs around the WebSocket transport itself.
