use std::io::ErrorKind;
use std::path::PathBuf;
use std::process::Stdio;
use std::sync::Arc;
use std::time::Duration;

use codex_config::types::StatusLineCommandConfig;
use ratatui::text::Line;
use serde::Serialize;
use tokio::io::AsyncWriteExt;
use tokio::process::Command;
use tokio::sync::Mutex;
use tokio::task::JoinHandle;

use crate::app_event::AppEvent;
use crate::app_event_sender::AppEventSender;
use crate::bottom_pane::StatusLineContent;

const DEFAULT_MAX_LINES: usize = 3;
const HARD_MAX_LINES: usize = 5;
const COMMAND_TIMEOUT: Duration = Duration::from_millis(500);
const MIN_REFRESH_INTERVAL: Duration = Duration::from_millis(300);
const OUTPUT_BYTES_CAP: usize = 64 * 1024;

#[derive(Clone)]
pub(crate) struct StatusLineCommandRunner {
    config: Arc<RunnerConfig>,
    state: Arc<Mutex<RunnerState>>,
}

#[derive(Debug)]
struct RunnerConfig {
    command: Vec<String>,
    max_lines: usize,
    refresh_interval: Option<Duration>,
    app_event_tx: AppEventSender,
}

#[derive(Debug, Default)]
struct RunnerState {
    latest_request: Option<RunRequest>,
    active_task: Option<JoinHandle<()>>,
    active_generation: u64,
    timer_pending: bool,
    warning_sent: bool,
}

#[derive(Clone, Debug)]
struct RunRequest {
    cwd: PathBuf,
    payload_json: String,
}

impl StatusLineCommandRunner {
    pub(crate) fn new(config: &StatusLineCommandConfig, app_event_tx: AppEventSender) -> Self {
        let max_lines = config
            .max_lines
            .unwrap_or(DEFAULT_MAX_LINES)
            .clamp(1, HARD_MAX_LINES);
        let refresh_interval = config
            .refresh_interval_ms
            .map(|millis| Duration::from_millis(millis).max(MIN_REFRESH_INTERVAL));
        Self {
            config: Arc::new(RunnerConfig {
                command: config.command.clone(),
                max_lines,
                refresh_interval,
                app_event_tx,
            }),
            state: Arc::new(Mutex::new(RunnerState::default())),
        }
    }

    pub(crate) fn request_update(&self, cwd: PathBuf, payload_json: String) {
        let runner = self.clone();
        tokio::spawn(async move {
            let generation = {
                let mut state = runner.state.lock().await;
                state.latest_request = Some(RunRequest { cwd, payload_json });
                state.active_generation = state.active_generation.saturating_add(1);
                let generation = state.active_generation;
                if let Some(active_task) = state.active_task.take() {
                    active_task.abort();
                }
                generation
            };
            let active_task = {
                let runner = runner.clone();
                tokio::spawn(async move {
                    tokio::time::sleep(MIN_REFRESH_INTERVAL).await;
                    runner.run_latest_request(generation).await;
                })
            };
            {
                let mut state = runner.state.lock().await;
                if state.active_generation == generation {
                    state.active_task = Some(active_task);
                } else {
                    active_task.abort();
                }
            }
        });
    }

    async fn run_latest_request(&self, generation: u64) {
        let request = {
            let mut state = self.state.lock().await;
            if state.active_generation != generation {
                return;
            }
            state.latest_request.take()
        };
        let Some(request) = request else {
            self.finish_active_task(generation).await;
            return;
        };

        match run_command(&self.config, request).await {
            Ok(Some(content)) => {
                self.config
                    .app_event_tx
                    .send(AppEvent::StatusLineCommandUpdated { content });
            }
            Ok(None) => {}
            Err(message) => self.warn_once(message).await,
        }

        self.finish_active_task(generation).await;
    }

    async fn finish_active_task(&self, generation: u64) {
        let mut state = self.state.lock().await;
        if state.active_generation != generation {
            return;
        }
        state.active_task = None;
        self.schedule_refresh_timer_locked(&mut state);
    }

    async fn warn_once(&self, message: String) {
        let mut state = self.state.lock().await;
        if state.warning_sent {
            return;
        }
        state.warning_sent = true;
        self.config
            .app_event_tx
            .send(AppEvent::StatusLineCommandWarning { message });
    }

    fn schedule_refresh_timer_locked(&self, state: &mut RunnerState) {
        let Some(refresh_interval) = self.config.refresh_interval else {
            return;
        };
        if state.timer_pending {
            return;
        }
        state.timer_pending = true;
        let runner = self.clone();
        tokio::spawn(async move {
            tokio::time::sleep(refresh_interval).await;
            {
                let mut state = runner.state.lock().await;
                state.timer_pending = false;
            }
            runner
                .config
                .app_event_tx
                .send(AppEvent::StatusLineCommandRefreshRequested);
        });
    }
}

async fn run_command(
    config: &RunnerConfig,
    request: RunRequest,
) -> Result<Option<StatusLineContent>, String> {
    let Some((program, args)) = config.command.split_first() else {
        return Err("Status line command is empty.".to_string());
    };

    let mut child = Command::new(program)
        .args(args)
        .current_dir(request.cwd)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .kill_on_drop(true)
        .spawn()
        .map_err(|err| format!("Failed to start status line command `{program}`: {err}"))?;

    if let Some(mut stdin) = child.stdin.take() {
        match stdin.write_all(request.payload_json.as_bytes()).await {
            Ok(()) => {}
            Err(err) if err.kind() == ErrorKind::BrokenPipe => {}
            Err(err) => return Err(format!("Failed to write status line payload: {err}")),
        }
    }

    let output = tokio::time::timeout(COMMAND_TIMEOUT, child.wait_with_output())
        .await
        .map_err(|_| "Status line command timed out after 500ms.".to_string())?
        .map_err(|err| format!("Failed to read status line command output: {err}"))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        let stderr = stderr.trim();
        let detail = if stderr.is_empty() {
            output.status.to_string()
        } else {
            format!("{}: {}", output.status, truncate_for_warning(stderr))
        };
        return Err(format!("Status line command failed: {detail}"));
    }

    Ok(status_line_content_from_stdout(
        &output.stdout,
        config.max_lines,
    ))
}

fn status_line_content_from_stdout(stdout: &[u8], max_lines: usize) -> Option<StatusLineContent> {
    let stdout = if stdout.len() > OUTPUT_BYTES_CAP {
        &stdout[..OUTPUT_BYTES_CAP]
    } else {
        stdout
    };
    let text = String::from_utf8_lossy(stdout);
    let text = text.trim_end_matches(['\r', '\n']);
    if text.trim().is_empty() {
        return None;
    }

    let lines = codex_ansi_escape::ansi_escape(text)
        .lines
        .into_iter()
        .take(max_lines)
        .collect::<Vec<Line<'static>>>();
    StatusLineContent::new(lines)
}

fn truncate_for_warning(message: &str) -> String {
    const MAX_CHARS: usize = 160;
    if message.chars().count() <= MAX_CHARS {
        return message.to_string();
    }
    let mut truncated = message.chars().take(MAX_CHARS).collect::<String>();
    truncated.push_str("...");
    truncated
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct StatusLineCommandPayload {
    pub(crate) model: PayloadModel,
    pub(crate) workspace: PayloadWorkspace,
    pub(crate) session: PayloadSession,
    pub(crate) status: PayloadStatus,
    pub(crate) context: PayloadContext,
    pub(crate) usage: PayloadUsage,
    pub(crate) git: PayloadGit,
    pub(crate) terminal: PayloadTerminal,
    pub(crate) agents: PayloadAgents,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct PayloadModel {
    pub(crate) id: String,
    pub(crate) display_name: String,
    pub(crate) reasoning_effort: Option<String>,
    pub(crate) service_tier: Option<String>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct PayloadWorkspace {
    pub(crate) cwd: String,
    pub(crate) current_dir: String,
    pub(crate) project_root: Option<String>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct PayloadSession {
    pub(crate) id: Option<String>,
    pub(crate) thread_title: Option<String>,
    pub(crate) codex_version: String,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct PayloadStatus {
    pub(crate) run_state: String,
    pub(crate) permissions: String,
    pub(crate) approval_mode: String,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct PayloadContext {
    pub(crate) window_tokens: Option<i64>,
    pub(crate) used_tokens: i64,
    pub(crate) used_percent: Option<i64>,
    pub(crate) remaining_percent: Option<i64>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct PayloadUsage {
    pub(crate) input_tokens: i64,
    pub(crate) output_tokens: i64,
    pub(crate) total_tokens: i64,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct PayloadGit {
    pub(crate) branch: Option<String>,
    pub(crate) pull_request_number: Option<u64>,
    pub(crate) pull_request_url: Option<String>,
    pub(crate) additions: Option<u64>,
    pub(crate) deletions: Option<u64>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct PayloadTerminal {
    pub(crate) columns: Option<u16>,
    pub(crate) rows: Option<u16>,
}

#[derive(Clone, Debug, Default, Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct PayloadAgents {
    pub(crate) total: usize,
    pub(crate) current: Option<String>,
    pub(crate) items: Vec<PayloadAgentItem>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct PayloadAgentItem {
    pub(crate) id: String,
    pub(crate) name: String,
    pub(crate) role: Option<String>,
    pub(crate) status: String,
}

impl PayloadAgents {
    pub(crate) fn upsert_item(&mut self, item: PayloadAgentItem) {
        if let Some(existing) = self
            .items
            .iter_mut()
            .find(|existing| existing.id == item.id)
        {
            *existing = item;
        } else {
            self.items.push(item);
        }
        self.total = self.items.len();
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::app_event::AppEvent;
    use crate::app_event_sender::AppEventSender;
    use pretty_assertions::assert_eq;
    use ratatui::style::Color;
    use tempfile::tempdir;
    use tokio::sync::mpsc::UnboundedReceiver;

    #[test]
    fn stdout_parser_caps_lines_and_preserves_ansi_styles() {
        let content = status_line_content_from_stdout(b"\x1b[31mone\x1b[0m\ntwo\nthree\nfour\n", 3)
            .expect("content");

        let lines = content.lines();
        assert_eq!(lines.len(), 3);
        assert_eq!(lines[0].spans[0].content.as_ref(), "one");
        assert_eq!(lines[0].spans[0].style.fg, Some(Color::Red));
        assert_eq!(lines[1].to_string(), "two");
        assert_eq!(lines[2].to_string(), "three");
    }

    #[test]
    fn empty_stdout_is_not_content() {
        assert_eq!(status_line_content_from_stdout(b"\n\n", 3), None);
    }

    #[test]
    fn payload_serializes_codex_native_camel_case_fields() {
        let payload = StatusLineCommandPayload {
            model: PayloadModel {
                id: "gpt-5.1-codex".to_string(),
                display_name: "GPT-5.1 Codex".to_string(),
                reasoning_effort: Some("high".to_string()),
                service_tier: Some("fast".to_string()),
            },
            workspace: PayloadWorkspace {
                cwd: "/repo/crate".to_string(),
                current_dir: "~/repo/crate".to_string(),
                project_root: Some("/repo".to_string()),
            },
            session: PayloadSession {
                id: Some("thread-id".to_string()),
                thread_title: Some("Fix status line".to_string()),
                codex_version: "0.135.0".to_string(),
            },
            status: PayloadStatus {
                run_state: "idle".to_string(),
                permissions: "workspace-write".to_string(),
                approval_mode: "on-request".to_string(),
            },
            context: PayloadContext {
                window_tokens: Some(200_000),
                used_tokens: 42_000,
                used_percent: Some(21),
                remaining_percent: Some(79),
            },
            usage: PayloadUsage {
                input_tokens: 100,
                output_tokens: 20,
                total_tokens: 120,
            },
            git: PayloadGit {
                branch: Some("feature/status-line".to_string()),
                pull_request_number: Some(123),
                pull_request_url: Some("https://github.com/openai/codex/pull/123".to_string()),
                additions: Some(10),
                deletions: Some(2),
            },
            terminal: PayloadTerminal {
                columns: Some(120),
                rows: Some(40),
            },
            agents: PayloadAgents {
                total: 2,
                current: Some("Lagrange [worker]".to_string()),
                items: vec![
                    PayloadAgentItem {
                        id: "agent-1".to_string(),
                        name: "Lagrange".to_string(),
                        role: Some("worker".to_string()),
                        status: "running".to_string(),
                    },
                    PayloadAgentItem {
                        id: "agent-2".to_string(),
                        name: "Hume".to_string(),
                        role: None,
                        status: "completed".to_string(),
                    },
                ],
            },
        };

        let value = serde_json::to_value(payload).expect("payload serializes");
        assert_eq!(value["session"]["threadTitle"], "Fix status line");
        assert_eq!(
            value["git"]["pullRequestUrl"],
            "https://github.com/openai/codex/pull/123"
        );
        assert_eq!(value["terminal"]["columns"], 120);
        assert_eq!(value["agents"]["total"], 2);
        assert_eq!(value["agents"]["current"], "Lagrange [worker]");
        assert_eq!(value["agents"]["items"][0]["status"], "running");
    }

    #[cfg(unix)]
    #[tokio::test]
    async fn runner_debounces_and_cancels_superseded_requests() {
        let (sender, mut rx) = test_sender();
        let runner = StatusLineCommandRunner::new(
            &test_config(
                vec![
                    "/bin/sh",
                    "-c",
                    r#"payload=$(cat); case "$payload" in *old*) sleep 1; printf old;; *) printf new;; esac"#,
                ],
                /*max_lines*/ None,
            ),
            sender,
        );
        let cwd = tempdir().expect("tempdir");

        runner.request_update(cwd.path().to_path_buf(), r#"{"value":"old"}"#.to_string());
        tokio::time::sleep(Duration::from_millis(50)).await;
        runner.request_update(cwd.path().to_path_buf(), r#"{"value":"new"}"#.to_string());

        let content = recv_status_line_update(&mut rx).await;
        assert_eq!(content_text(&content), "new");
        assert!(
            tokio::time::timeout(Duration::from_millis(250), recv_status_line_update(&mut rx))
                .await
                .is_err(),
            "superseded command should not publish stale output"
        );
    }

    #[cfg(unix)]
    #[tokio::test]
    async fn runner_clamps_configured_max_lines_to_hard_cap() {
        let (sender, mut rx) = test_sender();
        let runner = StatusLineCommandRunner::new(
            &test_config(
                vec![
                    "/bin/sh",
                    "-c",
                    "printf 'one\\ntwo\\nthree\\nfour\\nfive\\nsix\\n'",
                ],
                Some(99),
            ),
            sender,
        );
        let cwd = tempdir().expect("tempdir");

        runner.request_update(cwd.path().to_path_buf(), "{}".to_string());

        let content = recv_status_line_update(&mut rx).await;
        assert_eq!(
            content
                .lines()
                .iter()
                .map(ToString::to_string)
                .collect::<Vec<_>>(),
            vec!["one", "two", "three", "four", "five"]
        );
    }

    #[cfg(unix)]
    #[tokio::test]
    async fn runner_defaults_max_lines_to_three() {
        let (sender, mut rx) = test_sender();
        let runner = StatusLineCommandRunner::new(
            &test_config(
                vec!["/bin/sh", "-c", "printf 'one\\ntwo\\nthree\\nfour\\n'"],
                /*max_lines*/ None,
            ),
            sender,
        );
        let cwd = tempdir().expect("tempdir");

        runner.request_update(cwd.path().to_path_buf(), "{}".to_string());

        let content = recv_status_line_update(&mut rx).await;
        assert_eq!(
            content
                .lines()
                .iter()
                .map(ToString::to_string)
                .collect::<Vec<_>>(),
            vec!["one", "two", "three"]
        );
    }

    #[cfg(unix)]
    #[tokio::test]
    async fn runner_schedules_configured_refresh_interval() {
        let (sender, mut rx) = test_sender();
        let runner = StatusLineCommandRunner::new(
            &test_config_with_refresh(
                vec!["/bin/sh", "-c", "printf status"],
                /*refresh_interval_ms*/ Some(1),
                /*max_lines*/ None,
            ),
            sender,
        );
        let cwd = tempdir().expect("tempdir");

        runner.request_update(cwd.path().to_path_buf(), "{}".to_string());

        let content = recv_status_line_update(&mut rx).await;
        assert_eq!(content_text(&content), "status");
        recv_status_line_refresh_requested(&mut rx).await;
    }

    #[cfg(unix)]
    #[tokio::test]
    async fn run_command_empty_stdout_produces_no_content() {
        let config = test_runner_config(vec!["/bin/sh", "-c", "true"], /*max_lines*/ 3);
        let cwd = tempdir().expect("tempdir");

        let content = run_command(
            &config,
            RunRequest {
                cwd: cwd.path().to_path_buf(),
                payload_json: "{}".to_string(),
            },
        )
        .await
        .expect("empty output should not be a command failure");

        assert_eq!(content, None);
    }

    #[cfg(unix)]
    #[tokio::test]
    async fn run_command_non_zero_exit_is_error_without_content() {
        let config = test_runner_config(
            vec!["/bin/sh", "-c", "printf failure >&2; exit 7"],
            /*max_lines*/ 3,
        );
        let cwd = tempdir().expect("tempdir");

        let err = run_command(
            &config,
            RunRequest {
                cwd: cwd.path().to_path_buf(),
                payload_json: "{}".to_string(),
            },
        )
        .await
        .expect_err("non-zero exit should fail");

        assert!(err.contains("Status line command failed"));
        assert!(err.contains("failure"));
    }

    #[cfg(unix)]
    #[tokio::test]
    async fn run_command_timeout_is_error_without_partial_content() {
        let config = test_runner_config(
            vec!["/bin/sh", "-c", "printf partial; sleep 2"],
            /*max_lines*/ 3,
        );
        let cwd = tempdir().expect("tempdir");

        let err = run_command(
            &config,
            RunRequest {
                cwd: cwd.path().to_path_buf(),
                payload_json: "{}".to_string(),
            },
        )
        .await
        .expect_err("timeout should fail");

        assert_eq!(err, "Status line command timed out after 500ms.");
    }

    #[cfg(unix)]
    #[tokio::test]
    async fn runner_warns_once_for_repeated_failures() {
        let (sender, mut rx) = test_sender();
        let runner = StatusLineCommandRunner::new(
            &test_config(
                vec!["/bin/sh", "-c", "printf failure >&2; exit 7"],
                /*max_lines*/ None,
            ),
            sender,
        );
        let cwd = tempdir().expect("tempdir");

        runner.request_update(cwd.path().to_path_buf(), "{}".to_string());
        let warning = recv_status_line_warning(&mut rx).await;
        assert!(warning.contains("Status line command failed"));

        runner.request_update(cwd.path().to_path_buf(), "{}".to_string());
        assert!(
            tokio::time::timeout(
                Duration::from_millis(650),
                recv_status_line_warning(&mut rx)
            )
            .await
            .is_err(),
            "repeated failures should not emit repeated warnings"
        );
    }

    fn test_sender() -> (AppEventSender, UnboundedReceiver<AppEvent>) {
        let (tx, rx) = tokio::sync::mpsc::unbounded_channel();
        (AppEventSender::new(tx), rx)
    }

    fn test_config(command: Vec<&str>, max_lines: Option<usize>) -> StatusLineCommandConfig {
        test_config_with_refresh(command, /*refresh_interval_ms*/ None, max_lines)
    }

    fn test_config_with_refresh(
        command: Vec<&str>,
        refresh_interval_ms: Option<u64>,
        max_lines: Option<usize>,
    ) -> StatusLineCommandConfig {
        StatusLineCommandConfig {
            command: command.into_iter().map(ToString::to_string).collect(),
            refresh_interval_ms,
            max_lines,
        }
    }

    fn test_runner_config(command: Vec<&str>, max_lines: usize) -> RunnerConfig {
        let (sender, _rx) = test_sender();
        RunnerConfig {
            command: command.into_iter().map(ToString::to_string).collect(),
            max_lines,
            refresh_interval: None,
            app_event_tx: sender,
        }
    }

    async fn recv_status_line_update(rx: &mut UnboundedReceiver<AppEvent>) -> StatusLineContent {
        loop {
            let event = tokio::time::timeout(Duration::from_secs(2), rx.recv())
                .await
                .expect("timed out waiting for status line update")
                .expect("app event channel should stay open");
            if let AppEvent::StatusLineCommandUpdated { content } = event {
                return content;
            }
        }
    }

    async fn recv_status_line_warning(rx: &mut UnboundedReceiver<AppEvent>) -> String {
        loop {
            let event = tokio::time::timeout(Duration::from_secs(2), rx.recv())
                .await
                .expect("timed out waiting for status line warning")
                .expect("app event channel should stay open");
            if let AppEvent::StatusLineCommandWarning { message } = event {
                return message;
            }
        }
    }

    async fn recv_status_line_refresh_requested(rx: &mut UnboundedReceiver<AppEvent>) {
        loop {
            let event = tokio::time::timeout(Duration::from_secs(2), rx.recv())
                .await
                .expect("timed out waiting for status line refresh request")
                .expect("app event channel should stay open");
            if let AppEvent::StatusLineCommandRefreshRequested = event {
                return;
            }
        }
    }

    fn content_text(content: &StatusLineContent) -> String {
        content
            .lines()
            .iter()
            .map(ToString::to_string)
            .collect::<Vec<_>>()
            .join("\n")
    }
}
