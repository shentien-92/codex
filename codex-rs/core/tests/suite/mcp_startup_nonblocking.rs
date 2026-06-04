#![cfg(not(target_os = "windows"))]
#![allow(clippy::expect_used, clippy::unwrap_used)]

use anyhow::Result;
use anyhow::anyhow;
use codex_config::types::McpServerConfig;
use codex_config::types::McpServerTransportConfig;
use codex_features::Feature;
use codex_protocol::models::PermissionProfile;
use codex_protocol::protocol::AskForApproval;
use codex_protocol::protocol::EventMsg;
use codex_protocol::protocol::Op;
use codex_protocol::user_input::UserInput;
use core_test_support::responses::ResponseMock;
use core_test_support::responses::ResponsesRequest;
use core_test_support::responses::ev_assistant_message;
use core_test_support::responses::ev_completed;
use core_test_support::responses::ev_function_call_with_namespace;
use core_test_support::responses::ev_response_created;
use core_test_support::responses::mount_sse_once;
use core_test_support::responses::mount_sse_once_match;
use core_test_support::responses::sse;
use core_test_support::responses::start_mock_server;
use core_test_support::skip_if_no_network;
use core_test_support::stdio_server_bin;
use core_test_support::test_codex::TestCodex;
use core_test_support::test_codex::test_codex;
use core_test_support::test_codex::turn_permission_fields;
use core_test_support::wait_for_event_with_timeout;
use serde_json::Value;
use serde_json::json;
use std::collections::HashMap;
use std::time::Duration;

const READY_SERVER: &str = "ready_rmcp";
const SLOW_SERVER: &str = "slow_rmcp";
const READY_ECHO_TOOL: &str = "mcp__ready_rmcp__echo";
const SLOW_ECHO_TOOL: &str = "mcp__slow_rmcp__echo";
const STARTUP_DELAY_SECS: u64 = 5;
const WAIT_TIMEOUT: Duration = Duration::from_secs(/*secs*/ 20);

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn pending_optional_mcp_is_omitted_first_turn_and_visible_later() -> Result<()> {
    skip_if_no_network!(Ok(()));

    let server = start_mock_server().await;
    let first_mock = mount_sse_once(
        &server,
        sse(vec![
            ev_response_created("resp-1"),
            ev_assistant_message("msg-1", "first done"),
            ev_completed("resp-1"),
        ]),
    )
    .await;
    let second_mock = mount_sse_once(
        &server,
        sse(vec![
            ev_response_created("resp-2"),
            ev_assistant_message("msg-2", "second done"),
            ev_completed("resp-2"),
        ]),
    )
    .await;

    let mut builder = test_codex().with_config(configure_ready_and_slow_mcp_servers);
    let test = builder.build(&server).await?;

    test.submit_turn_with_approval_and_permission_profile(
        "first turn while slow MCP is still starting",
        AskForApproval::Never,
        PermissionProfile::Disabled,
    )
    .await?;
    let first_tools = request_tool_names(&first_mock.single_request());
    assert!(
        first_tools.iter().any(|tool| tool == READY_ECHO_TOOL),
        "ready MCP tool should be visible on first turn: {first_tools:?}"
    );
    assert!(
        !first_tools.iter().any(|tool| tool == SLOW_ECHO_TOOL),
        "pending optional MCP tool should be omitted on first turn: {first_tools:?}"
    );

    wait_for_mcp_ready(&test, SLOW_SERVER).await?;
    test.submit_turn_with_approval_and_permission_profile(
        "second turn after slow MCP is ready",
        AskForApproval::Never,
        PermissionProfile::Disabled,
    )
    .await?;
    let second_tools = request_tool_names(&second_mock.single_request());
    assert!(
        second_tools.iter().any(|tool| tool == READY_ECHO_TOOL),
        "ready MCP tool should remain visible later: {second_tools:?}"
    );
    assert!(
        second_tools.iter().any(|tool| tool == SLOW_ECHO_TOOL),
        "slow optional MCP tool should become visible after readiness: {second_tools:?}"
    );

    Ok(())
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn spawned_subagent_first_turn_omits_pending_optional_mcp() -> Result<()> {
    skip_if_no_network!(Ok(()));

    let server = start_mock_server().await;
    let child_prompt = "child: inspect MCP tool visibility";
    let spawn_args = serde_json::to_string(&json!({ "message": child_prompt }))?;
    mount_sse_once_match(
        &server,
        |req: &wiremock::Request| request_body_contains(req, "spawn a subagent"),
        sse(vec![
            ev_response_created("resp-parent-1"),
            ev_function_call_with_namespace(
                "spawn-call-1",
                "multi_agent_v1",
                "spawn_agent",
                &spawn_args,
            ),
            ev_completed("resp-parent-1"),
        ]),
    )
    .await;
    let child_mock = mount_sse_once_match(
        &server,
        |req: &wiremock::Request| request_body_contains(req, child_prompt),
        sse(vec![
            ev_response_created("resp-child-1"),
            ev_assistant_message("msg-child-1", "child done"),
            ev_completed("resp-child-1"),
        ]),
    )
    .await;
    mount_sse_once_match(
        &server,
        |req: &wiremock::Request| request_body_contains(req, "spawn-call-1"),
        sse(vec![
            ev_response_created("resp-parent-2"),
            ev_assistant_message("msg-parent-2", "parent done"),
            ev_completed("resp-parent-2"),
        ]),
    )
    .await;

    let mut builder = test_codex().with_config(configure_ready_and_slow_mcp_servers);
    let test = builder.build(&server).await?;
    submit_collaboration_turn(&test, "spawn a subagent while slow MCP starts").await?;

    let child = wait_for_matching_request(&child_mock, "child model request", |request| {
        request.body_contains_text(child_prompt)
    })
    .await?;
    let child_tools = request_tool_names(&child);
    assert!(
        child_tools.iter().any(|tool| tool == READY_ECHO_TOOL),
        "ready MCP tool should be visible to spawned subagent: {child_tools:?}"
    );
    assert!(
        !child_tools.iter().any(|tool| tool == SLOW_ECHO_TOOL),
        "pending optional MCP tool should be omitted from spawned subagent first turn: {child_tools:?}"
    );

    Ok(())
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn required_mcp_failure_is_reported_during_startup() -> Result<()> {
    skip_if_no_network!(Ok(()));

    let server = start_mock_server().await;
    let mut builder = test_codex().with_config(|config| {
        let mut servers = config.mcp_servers.get().clone();
        servers.insert(
            "required_missing".to_string(),
            McpServerConfig {
                transport: McpServerTransportConfig::Stdio {
                    command: "codex-required-mcp-command-that-does-not-exist".to_string(),
                    args: Vec::new(),
                    env: None,
                    env_vars: Vec::new(),
                    cwd: None,
                },
                environment_id: "local".to_string(),
                enabled: true,
                required: true,
                supports_parallel_tool_calls: false,
                disabled_reason: None,
                startup_timeout_sec: Some(Duration::from_millis(/*millis*/ 100)),
                tool_timeout_sec: None,
                default_tools_approval_mode: None,
                enabled_tools: None,
                disabled_tools: None,
                scopes: None,
                oauth: None,
                oauth_resource: None,
                tools: HashMap::new(),
            },
        );
        config
            .mcp_servers
            .set(servers)
            .expect("test mcp servers should accept any configuration");
    });
    let error = match builder.build(&server).await {
        Ok(_) => anyhow::bail!("required MCP startup failure should prevent session startup"),
        Err(error) => error,
    };
    assert!(
        error
            .to_string()
            .contains("required MCP servers failed to initialize"),
        "unexpected required MCP startup error: {error:#}"
    );
    assert!(
        error.to_string().contains("required_missing"),
        "required MCP startup error should identify the failed server: {error:#}"
    );

    Ok(())
}

fn configure_ready_and_slow_mcp_servers(config: &mut codex_core::config::Config) {
    config
        .features
        .disable(Feature::EnableRequestCompression)
        .expect("test config should allow feature update");
    let rmcp_test_server_bin = stdio_server_bin().expect("stdio MCP test server binary");
    let mut servers = config.mcp_servers.get().clone();
    servers.insert(
        READY_SERVER.to_string(),
        stdio_mcp_server_config_with_args(
            rmcp_test_server_bin.clone(),
            Vec::new(),
            Some(HashMap::from([(
                "MCP_TEST_VALUE".to_string(),
                "ready".to_string(),
            )])),
        ),
    );
    servers.insert(
        SLOW_SERVER.to_string(),
        stdio_mcp_server_config_with_args(
            "/bin/sh".to_string(),
            vec![
                "-c".to_string(),
                format!("sleep {STARTUP_DELAY_SECS}; exec \"$1\""),
                "sh".to_string(),
                rmcp_test_server_bin,
            ],
            Some(HashMap::from([(
                "MCP_TEST_VALUE".to_string(),
                "slow".to_string(),
            )])),
        ),
    );
    config
        .mcp_servers
        .set(servers)
        .expect("test mcp servers should accept any configuration");
}

fn stdio_mcp_server_config_with_args(
    command: String,
    args: Vec<String>,
    env: Option<HashMap<String, String>>,
) -> McpServerConfig {
    McpServerConfig {
        transport: McpServerTransportConfig::Stdio {
            command,
            args,
            env,
            env_vars: Vec::new(),
            cwd: None,
        },
        environment_id: "local".to_string(),
        enabled: true,
        required: false,
        supports_parallel_tool_calls: false,
        disabled_reason: None,
        startup_timeout_sec: Some(Duration::from_secs(/*secs*/ 10)),
        tool_timeout_sec: None,
        default_tools_approval_mode: None,
        enabled_tools: None,
        disabled_tools: None,
        scopes: None,
        oauth: None,
        oauth_resource: None,
        tools: HashMap::new(),
    }
}

fn request_tool_names(request: &ResponsesRequest) -> Vec<String> {
    let mut names = Vec::new();
    collect_tool_names(
        &request.body_json()["tools"],
        /*namespace*/ None,
        &mut names,
    );
    names
}

fn collect_tool_names(value: &Value, namespace: Option<&str>, names: &mut Vec<String>) {
    match value {
        Value::Array(values) => {
            for value in values {
                collect_tool_names(value, namespace, names);
            }
        }
        Value::Object(object) => {
            let next_namespace = if object.get("type").and_then(Value::as_str) == Some("namespace")
            {
                object.get("name").and_then(Value::as_str)
            } else {
                namespace
            };
            if let Some(name) = object.get("name").and_then(Value::as_str) {
                names.push(name.to_string());
                if object.get("type").and_then(Value::as_str) == Some("function")
                    && let Some(namespace) = namespace
                {
                    names.push(format!("{namespace}__{name}"));
                }
            }
            if let Some(tools) = object.get("tools") {
                collect_tool_names(tools, next_namespace, names);
            }
        }
        _ => {}
    }
}

async fn wait_for_mcp_ready(test: &TestCodex, server_name: &str) -> Result<()> {
    let startup_event = wait_for_event_with_timeout(
        &test.codex,
        |event| match event {
            EventMsg::McpStartupComplete(summary) => {
                summary.ready.iter().any(|server| server == server_name)
                    || summary
                        .failed
                        .iter()
                        .any(|failure| failure.server == server_name)
                    || summary.cancelled.iter().any(|server| server == server_name)
            }
            _ => false,
        },
        WAIT_TIMEOUT,
    )
    .await;
    let EventMsg::McpStartupComplete(summary) = startup_event else {
        unreachable!("event guard guarantees McpStartupComplete");
    };
    if let Some(failure) = summary
        .failed
        .iter()
        .find(|failure| failure.server == server_name)
    {
        let error = &failure.error;
        anyhow::bail!("MCP server {server_name} failed to start: {error}");
    }
    if summary.cancelled.iter().any(|server| server == server_name) {
        anyhow::bail!("MCP server {server_name} startup was cancelled");
    }
    if !summary.ready.iter().any(|server| server == server_name) {
        anyhow::bail!("expected MCP server {server_name} ready; summary: {summary:?}");
    }
    Ok(())
}

async fn submit_collaboration_turn(test: &TestCodex, prompt: &str) -> Result<()> {
    let session_model = test.session_configured.model.clone();
    let cwd = test.config.cwd.to_path_buf();
    let (sandbox_policy, permission_profile) =
        turn_permission_fields(PermissionProfile::workspace_write(), cwd.as_path());
    test.codex
        .submit(Op::UserInput {
            items: vec![UserInput::Text {
                text: prompt.into(),
                text_elements: Vec::new(),
            }],
            environments: None,
            final_output_json_schema: None,
            responsesapi_client_metadata: None,
            additional_context: Default::default(),
            thread_settings: codex_protocol::protocol::ThreadSettingsOverrides {
                cwd: Some(cwd),
                approval_policy: Some(AskForApproval::OnRequest),
                sandbox_policy: Some(sandbox_policy),
                permission_profile,
                collaboration_mode: Some(codex_protocol::config_types::CollaborationMode {
                    mode: codex_protocol::config_types::ModeKind::Default,
                    settings: codex_protocol::config_types::Settings {
                        model: session_model,
                        reasoning_effort: None,
                        developer_instructions: None,
                    },
                }),
                ..Default::default()
            },
        })
        .await?;

    let turn_started = wait_for_event_with_timeout(
        &test.codex,
        |event| matches!(event, EventMsg::TurnStarted(_)),
        WAIT_TIMEOUT,
    )
    .await;
    let EventMsg::TurnStarted(turn_started) = turn_started else {
        unreachable!("event guard guarantees TurnStarted");
    };
    wait_for_event_with_timeout(
        &test.codex,
        |event| match event {
            EventMsg::TurnComplete(event) => event.turn_id == turn_started.turn_id,
            _ => false,
        },
        WAIT_TIMEOUT,
    )
    .await;
    Ok(())
}

async fn wait_for_matching_request<F>(
    mock: &ResponseMock,
    label: &str,
    mut predicate: F,
) -> Result<ResponsesRequest>
where
    F: FnMut(&ResponsesRequest) -> bool,
{
    tokio::time::timeout(WAIT_TIMEOUT, async {
        loop {
            if let Some(request) = mock
                .requests()
                .into_iter()
                .find(|request| predicate(request))
            {
                return Ok::<ResponsesRequest, anyhow::Error>(request);
            }
            tokio::time::sleep(Duration::from_millis(/*millis*/ 20)).await;
        }
    })
    .await
    .map_err(|_| anyhow!("timed out waiting for {label}"))?
}

fn request_body_contains(req: &wiremock::Request, text: &str) -> bool {
    std::str::from_utf8(&req.body).is_ok_and(|body| body.contains(text))
}
