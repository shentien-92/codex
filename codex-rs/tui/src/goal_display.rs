use codex_app_server_protocol::ThreadGoalStatus;

pub(crate) fn format_goal_elapsed_seconds(seconds: i64) -> String {
    let seconds = seconds.max(0) as u64;
    if seconds < 60 {
        return format!("{seconds}s");
    }

    let minutes = seconds / 60;
    if minutes < 60 {
        return format!("{minutes}m");
    }

    let hours = minutes / 60;
    let remaining_minutes = minutes % 60;
    if hours >= 24 {
        let days = hours / 24;
        let remaining_hours = hours % 24;
        return format!("{days}d {remaining_hours}h {remaining_minutes}m");
    }

    if remaining_minutes == 0 {
        format!("{hours}h")
    } else {
        format!("{hours}h {remaining_minutes}m")
    }
}

pub(crate) fn goal_status_label(status: ThreadGoalStatus) -> &'static str {
    match status {
        ThreadGoalStatus::Active => "active",
        ThreadGoalStatus::Paused => "paused",
        ThreadGoalStatus::Blocked => "blocked",
        ThreadGoalStatus::UsageLimited => "usage limited",
        ThreadGoalStatus::BudgetLimited => "limited by budget",
        ThreadGoalStatus::Complete => "complete",
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use pretty_assertions::assert_eq;

    #[test]
    fn format_goal_elapsed_seconds_is_compact() {
        assert_eq!(format_goal_elapsed_seconds(/*seconds*/ 0), "0s");
        assert_eq!(format_goal_elapsed_seconds(/*seconds*/ 59), "59s");
        assert_eq!(format_goal_elapsed_seconds(/*seconds*/ 60), "1m");
        assert_eq!(format_goal_elapsed_seconds(30 * 60), "30m");
        assert_eq!(format_goal_elapsed_seconds(90 * 60), "1h 30m");
        assert_eq!(format_goal_elapsed_seconds(2 * 60 * 60), "2h");
        let just_before_one_day = 24 * 60 * 60 - 1;
        assert_eq!(format_goal_elapsed_seconds(just_before_one_day), "23h 59m");

        let one_day = 24 * 60 * 60;
        assert_eq!(format_goal_elapsed_seconds(one_day), "1d 0h 0m");

        let almost_three_days = 2 * 24 * 60 * 60 + 23 * 60 * 60 + 42 * 60;
        assert_eq!(format_goal_elapsed_seconds(almost_three_days), "2d 23h 42m");
    }
}
