# Recent PRD completion audit

## Goal

Audit recent archived PRDs for missed acceptance criteria and create follow-up implementation tasks for any gaps.

## Requirements

- Scope recent PRDs as archived Trellis tasks in `archive/2026-06`.
- Read each PRD and identify concrete acceptance criteria or must-have requirements.
- Compare criteria against current code, tests, task quality notes, and commit history where available.
- Record a concise audit table with one row per task and a pass/gap/needs-follow-up status.
- For any missed feature or unverifiable high-risk gap, create or update a follow-up Trellis task with enough context to implement it.
- Do not make unrelated product/code changes during the audit.

## Acceptance Criteria

- [ ] Every archived June PRD with a `prd.md` is listed in an audit result artifact.
- [ ] Each listed PRD has evidence notes: relevant files/tests/commits or reason it is not verifiable.
- [ ] Known missed MCP startup nonblocking gap is reflected as completed by `.trellis/tasks/archive/2026-06/06-04-mcp-startup-nonblocking-gap-completion`.
- [ ] Any newly discovered missed feature has a follow-up task, or the audit records why it is out of scope/not actionable.
- [ ] Audit task runs Trellis gates and is archived when complete.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
