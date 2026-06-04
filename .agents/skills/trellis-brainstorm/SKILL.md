---
name: trellis-brainstorm
description: "Guides collaborative requirements discovery before implementation. Creates task directory, seeds PRD, asks high-value questions one at a time, researches technical choices, and converges on MVP scope. Use when requirements are unclear, there are multiple valid approaches, or the user describes a new feature or complex task."
---

# Trellis Brainstorm

## Non-Negotiable Interview Contract

Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

Ask the questions one at a time.

## Non-Negotiable Evidence Rule

If a question can be answered by exploring the codebase, explore the codebase instead.

This is mandatory. Before asking the user a question, first check whether the answer is already available in code, tests, configs, docs, existing specs, or task history.

Do not ask the user to confirm facts that the repository can answer. Ask only for product intent, preference, scope, risk tolerance, or decisions that remain ambiguous after inspection.

---

Use this skill during Phase 1 planning to turn the user's request into clear requirements and planning artifacts.

## Preconditions

Use this skill only after task-creation consent has been given and the user is ready to enter Trellis planning.

If no task exists yet, create one:

```bash
TASK_DIR=$(python3 ./.trellis/scripts/task.py create "<short task title>" --slug <slug>)
```

Use a concise title from the user's request. Use a slug without a date prefix. `task.py create` adds the `MM-DD-` directory prefix automatically.

`task.py create` creates the default `prd.md`. Update that file with the current understanding before asking follow-up questions.

## Planning Flow

1. Capture the user's request and initial known facts in `prd.md`.
2. Inspect available evidence before asking questions:
   - code, tests, fixtures, and configs
   - README files, docs, existing specs, and domain notes
   - `.trellis/spec/context/CONTEXT.md` whenever the task uses project/domain terminology
   - `.trellis/spec/adr/` when the task involves hard-to-reverse architecture choices or trade-offs
   - related Trellis tasks, research files, and session history when present
3. Separate what you found into:
   - confirmed facts
   - product intent still needed from the user
   - scope or risk decisions still needed from the user
   - likely out-of-scope items
4. Ask the single highest-value remaining question.
5. Include your recommended answer with the question.
6. After each user answer, update `prd.md` before continuing.
7. For complex tasks, create or update `design.md` and `implement.md` before implementation starts.

For complex or multi-deliverable tasks, split work into vertical slices after the `prd.md` stabilizes. A vertical slice delivers one independently verifiable behavior end-to-end. It may include data shape, command/API behavior, UI, tests, docs, and migration work when those are needed for that behavior. Avoid horizontal slices like "build schema", "build API", "add tests", or "write docs" unless the task is purely infrastructural and that layer is the user-visible deliverable.

Record the vertical-slice breakdown in the artifact that owns execution:

- parent `prd.md` task map when creating child tasks
- child `prd.md` acceptance criteria for independently executable work
- `implement.md` ordered checklist for a single complex task

Do not use the parent/child tree as an implicit dependency model. Write dependency ordering in each affected child `prd.md` / `implement.md`.

For each slice, capture:

- the user-visible or operator-visible outcome
- the requirements / acceptance criteria it covers
- dependency order, if any
- `AFK` when the slice can be implemented without more user input, or `HITL` when it needs a product, design, architecture, migration, or risk decision checkpoint
- expected validation evidence
- relevant spec / research context to include in `implement.jsonl` or `check.jsonl` when sub-agent context is used

Do not invent a project-specific product/spec hierarchy. If the repository already has product, domain, or spec docs, use them. If it does not, proceed with the evidence that exists.

For Trellis-managed domain context, `.trellis/spec/context/CONTEXT.md` is the canonical glossary and boundary document. ADRs are optional and live under `.trellis/spec/adr/`; know the directory exists and inspect it when planning work with architectural trade-offs.

## Question Rules

Ask only one question per message. Prefer the host/native Ask Question tool for blocking/preference/confirmation questions when available and suitable; fall back to normal text when unavailable or unsuitable.

Each question must include:

- the decision needed
- why the answer matters
- your recommended answer
- the trade-off if the user chooses differently

Do not ask process questions such as whether to search, inspect files, or continue brainstorming. Do the evidence work directly. Ask the user only when the remaining issue is a product decision, preference, scope boundary, or risk tolerance choice. When that user input is needed, prefer the host's native Ask Question / choice UI when available and suitable. In Claude Code, use `AskUserQuestion`; on other hosts, use the equivalent native ask-question or choice interface. If the host lacks that capability or the question cannot be expressed clearly through it, fall back to a normal text question.

## Artifact Rules

`prd.md` records requirements and acceptance:

- goal and user value
- confirmed facts
- requirements
- acceptance criteria
- out of scope
- open questions that still block planning

`design.md` records technical design for complex tasks:

- architecture and boundaries
- data flow and contracts
- compatibility and migration notes
- important trade-offs
- operational or rollback considerations

`implement.md` records execution planning for complex tasks:

- ordered implementation checklist
- validation commands
- risky files or rollback points
- follow-up checks before `task.py start`

Lightweight tasks may have only `prd.md`. Complex tasks must have `prd.md`, `design.md`, and `implement.md` before `task.py start`.

`implement.md` is not a replacement for `implement.jsonl`. Use JSONL files only for manifest-style spec and research references when the task needs them.

## Quality Bar

Before declaring planning ready:

- `prd.md` contains testable acceptance criteria.
- Repository-answerable questions have already been answered through inspection.
- Remaining open questions are genuinely about user intent or scope.
- Complex tasks have `design.md` and `implement.md`.
- The user has reviewed the final planning artifacts or explicitly approved proceeding.

Do not start implementation until the user approves or asks for implementation. Prefer the host/native Ask Question tool for final approval when available and suitable; fall back to normal text when unavailable or unsuitable.
