use crate::status_line_command::PayloadAgentItem;
use serde::Deserialize;

const START_MARKER: &str = "<subagent_notification>";
const END_MARKER: &str = "</subagent_notification>";

#[derive(Debug, Deserialize)]
struct SubagentNotificationPayload {
    #[serde(alias = "agent_id")]
    agent_path: String,
    status: SubagentNotificationStatus,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "snake_case")]
enum SubagentNotificationStatus {
    PendingInit,
    Running,
    #[allow(dead_code)]
    Completed(Option<String>),
    #[allow(dead_code)]
    Errored(String),
    Interrupted,
    Shutdown,
    NotFound,
}

impl SubagentNotificationStatus {
    fn status_line_label(&self) -> &'static str {
        match self {
            Self::PendingInit => "pendingInit",
            Self::Running => "running",
            Self::Completed(_) => "completed",
            Self::Errored(_) => "errored",
            Self::Interrupted => "interrupted",
            Self::Shutdown => "shutdown",
            Self::NotFound => "notFound",
        }
    }
}

pub(crate) fn status_line_agent_item_from_notification(text: &str) -> Option<PayloadAgentItem> {
    let start = text.find(START_MARKER)? + START_MARKER.len();
    let end = text[start..].find(END_MARKER)? + start;
    let payload =
        serde_json::from_str::<SubagentNotificationPayload>(text[start..end].trim()).ok()?;
    let name = payload
        .agent_path
        .rsplit('/')
        .next()
        .filter(|name| !name.is_empty())
        .unwrap_or(payload.agent_path.as_str())
        .to_string();

    Some(PayloadAgentItem {
        id: payload.agent_path,
        name,
        role: None,
        status: payload.status.status_line_label().to_string(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use pretty_assertions::assert_eq;

    #[test]
    fn parses_subagent_notification_for_status_line() {
        let item = status_line_agent_item_from_notification(
            r#"<subagent_notification>{"agent_path":"/root/worker","status":{"completed":"done"}}</subagent_notification>"#,
        )
        .expect("notification parses");

        assert_eq!(
            item,
            PayloadAgentItem {
                id: "/root/worker".to_string(),
                name: "worker".to_string(),
                role: None,
                status: "completed".to_string(),
            }
        );
    }
}
