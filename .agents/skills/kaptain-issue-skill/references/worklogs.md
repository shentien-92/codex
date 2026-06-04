# 工作日志与工时

## 工作日志工具

- `list_issue_worklogs`
- `add_issue_worklog`
- `update_issue_worklog`

## 工时规则

1. `workTimeMinutes` 和 `workHours` 必须二选一
2. 工时最终按分钟发送给后端
3. 默认不允许 0 工时
4. 只有在需要后端特殊联动时才使用 `skipWhenWorkTimeIsZero=true`
