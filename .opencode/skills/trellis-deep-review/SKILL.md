---
name: trellis-deep-review
description: "Optional Trellis deep review gate. Use only when the user explicitly asks for deep review, strict review, review until OK, or final verification."
---

# Trellis Deep Review

Use this skill to run a strict, evidence-based review gate before declaring work complete. It is optional: Trellis distributes it by default so users can ask for it, but normal workflow phases do not require it.

Deep review is different from a normal quality check. A quality check asks whether commands pass and obvious requirements are covered. Deep review asks whether the submitted work is genuinely complete, whether the evidence proves the real surface works, and whether any missing proof should block completion.

## Core Contract

- Review only. The reviewer must not implement, edit, patch, or delegate.
- Approval requires evidence, not explanation.
- Missing evidence is a rejection.
- "Looks good but..." is a rejection.
- The only passing verdict is `UNCONDITIONAL APPROVAL`.

## Step 1: Choose The Evidence Store

Use the existing task or workflow directory when one exists.

Preferred locations:

1. Current Trellis task: `.trellis/tasks/<task-id>/evidence/`
2. Existing non-Trellis task/workflow directory
3. Temporary session-only directory: `/tmp/deep-review-<timestamp>-<slug>/`

In a Trellis project, do not create a separate `.deep-review/` directory. The Trellis task is the unit of traceability and should own review evidence. If the active task is unclear, identify or create the Trellis task before collecting persistent review evidence.

Use compact evidence by default:

```text
evidence/
├── review-packet.md
├── evidence.jsonl
└── reviewer-rounds/
    ├── round-1.md
    ├── round-2.md
    └── approval.md
```

Add raw artifact directories only when they add review value:

```text
evidence/
├── artifacts/
├── commands/
├── logs/
└── screenshots/
```

## Step 2: Capture Evidence

Use deterministic names for raw artifacts so multi-round reviews remain readable:

```text
commands/<YYYYMMDD-HHMM>-<scenario-slug>.txt
logs/<YYYYMMDD-HHMM>-<scenario-slug>.log
screenshots/<YYYYMMDD-HHMM>-<scenario-slug>.png
```

Stable canonical names are also fine for one-off task artifacts, such as `head-<sha>.diff`, `current-diff.diff`, or `approval.md`.

Write `evidence.jsonl` before asking for review. It records structured facts; `review-packet.md` records narrative judgment, covered/uncovered scope, risks, and commit decisions.

Use one JSON object per line. Common event kinds:

- `command`: command run, exit code, result, excerpt, optional artifact path
- `diff`: commit or working-tree diff source, optional artifact path
- `status`: repository, service, environment, or scenario status snapshot
- `skip`: skipped check with exact reason
- `artifact`: raw artifact metadata, sanitization, or external storage reference
- `process_failure`: reviewer, sub-agent, tool, or infrastructure failure that affects the review process

For command records, include:

- command or scenario name
- working directory
- timestamp
- exit code or PASS/FAIL result
- relevant output excerpt
- artifact path only when raw output is committed
- scenario/result mapping
- skipped checks and exact reason

Example `evidence.jsonl`:

```jsonl
{"kind":"command","name":"focused-template-tests","command":"pnpm --filter @qunhe/trellis exec vitest run test/templates/codex.test.ts test/templates/trellis.test.ts","cwd":"/repo","timestamp":"2026-06-04T00:46:38Z","exit_code":0,"result":"passed","excerpt":"Test Files 2 passed; Tests 39 passed","artifact_path":null}
{"kind":"diff","name":"main-change","source":"git show 937e41d","commit":"937e41d","artifact_path":null,"reason":"reproducible from commit SHA"}
{"kind":"skip","name":"gitnexus-detect-changes","reason":"GitNexus MCP tool unavailable in this session"}
{"kind":"process_failure","name":"trellis-implement-dispatch","result":"failed","reason":"child model resolution error","effect":"implementation completed in main session; not an implementation verdict"}
```

Raw artifacts are optional. Prefer `artifact_path: null` plus a reproducible source when the evidence can be recreated from a commit SHA, command line, stable URL, or existing log system. Commit raw artifacts only when output is long, failure-specific, non-reproducible, reviewer-requested, or needed to prove the real surface. Do not paste huge logs into the review packet.

If raw text artifacts will be committed, it is acceptable to mechanically normalize them for commit hygiene, such as removing trailing whitespace or extra blank lines at EOF. Record the original command and source commit/path so the artifact remains reproducible. The canonical source is the command output, referenced commit, screenshot, or external log system; the committed file can be a review-normalized copy.

### Review Artifact Commit Policy

In Trellis tasks, review artifacts are durable task evidence and should usually be committed so they archive with the task.

Commit review artifacts when they are:

- task-relevant
- reasonably sized
- free of secrets, credentials, private customer data, and sensitive logs

Do not commit raw artifacts when they contain sensitive data, large binary blobs, or noisy logs that do not improve traceability. Sanitize or summarize them instead. If an artifact is omitted, record the omission and exact reason in `evidence.jsonl`, `review-packet.md`, and the final report.

Before committing review artifacts, run this checklist:

- `git diff --cached --check` passes for staged artifacts.
- `git check-ignore <artifact-path>` does not report task evidence that should be committed, or the ignore exception is intentionally documented.
- No secrets, credentials, private customer data, or sensitive logs are present.
- `reviewer-rounds/approval.md` exists before reporting `UNCONDITIONAL APPROVAL`.
- Any omitted, sanitized, or external-only artifacts are listed with reasons in `evidence.jsonl`, `review-packet.md`, and the final report.

## Step 3: Build The Review Packet

Create `review-packet.md` with these sections:

```markdown
# Deep Review Packet

## Goal

<Original user goal and clarified success target.>

## Success Criteria

- <Concrete condition that must be true.>

## Constraints And Non-Goals

- <Rules, compatibility requirements, project conventions, or explicit non-goals.>

## Covered Scope

- <Work, commits, files, requirements, or scenarios this review verdict should cover.>

## Uncovered Scope

- <Adjacent work, same-commit changes, generated files, or known side changes this review verdict does not cover.>

## Changed Files

- <Path and brief purpose.>

## Diff

<Diff source such as commit SHA / git command, or raw artifact path only when needed.>

## Context

<Full file contents or excerpts needed to understand the diff.>

## Verification Evidence

- <Evidence summary with links to `evidence.jsonl` records and raw artifact paths only when needed.>

## Known Risks And Skipped Checks

- <Uncertainty, skipped verification, environment limitation, or residual risk.>
```

If a required section is missing, record it honestly. Do not hide missing evidence.

### Packet Draft Recipe

Use this recipe to create a first-pass packet, then edit it manually before review. The generated draft is not a substitute for judgment: you must still fill in success criteria, constraints, covered/uncovered scope, known risks, and skipped checks honestly.

```bash
TASK_DIR=".trellis/tasks/<task-id>"
EVIDENCE_DIR="$TASK_DIR/evidence"
STAMP="$(date +%Y%m%d-%H%M)"
mkdir -p "$EVIDENCE_DIR/reviewer-rounds"

git status --short > "$EVIDENCE_DIR/.status.tmp"
STATUS_EXCERPT="$(tr '\n' ';' < "$EVIDENCE_DIR/.status.tmp")"
rm "$EVIDENCE_DIR/.status.tmp"

cat > "$EVIDENCE_DIR/evidence.jsonl" <<EOF
{"kind":"status","name":"git-status","command":"git status --short","timestamp":"${STAMP}","result":"recorded","excerpt":"${STATUS_EXCERPT}","artifact_path":null}
{"kind":"diff","name":"current-diff","source":"git diff --find-renames --find-copies","timestamp":"${STAMP}","artifact_path":null,"reason":"working-tree diff is reproducible during the review session; commit raw diff only if reviewer cannot access the working tree"}
EOF

cat > "$EVIDENCE_DIR/review-packet.md" <<EOF
# Deep Review Packet

## Goal

<Original user goal and clarified success target.>

## Success Criteria

- <Concrete condition that must be true.>

## Constraints And Non-Goals

- <Rules, compatibility requirements, project conventions, or explicit non-goals.>

## Covered Scope

- <Commits, files, requirements, and scenarios this review verdict should cover.>

## Uncovered Scope

- <Adjacent work, same-commit changes, generated files, or known side changes this review verdict does not cover.>

## Changed Files

- <Run `git diff --stat` or inspect the commit, then replace this with path-by-path purpose notes.>

## Diff

- See `evidence.jsonl` diff records; add a raw diff artifact only when the diff is not reproducible from a commit SHA or working tree.

## Context

- <Full file contents, excerpts, task docs, specs, or links needed to understand the diff.>

## Verification Evidence

- See `evidence.jsonl`; summarize the command/scenario evidence relevant to the review.

## Known Risks And Skipped Checks

- <Uncertainty, skipped verification, environment limitation, or residual risk.>
EOF
```

For committed changes, prefer a compact diff record instead of committing a raw diff file:

```jsonl
{"kind":"diff","name":"main-change","source":"git show <commit-sha>","commit":"<commit-sha>","artifact_path":null,"reason":"reproducible from commit SHA"}
```

Commit a raw diff artifact, such as `commands/<YYYYMMDD-HHMM>-<commit-sha>.diff`, only when the reviewer cannot access the commit, the review is over an unstable working tree, or the diff must be frozen independently from Git history.

## Step 4: Invoke A Read-Only Reviewer

Prefer a dedicated read-only reviewer agent if the host provides one. If not, ask an available high-reasoning agent to follow this assignment. The message must be self-contained.

```text
TASK: Deep review the submitted work. Review only. Do not implement, edit, patch, or delegate.

You are a deep verification reviewer.

Your job is to decide whether the submitted work is genuinely complete.
You are not checking whether commands were run; you are checking whether the goal is satisfied with sufficient evidence.

Verdict rules:
- Return UNCONDITIONAL APPROVAL only when every success criterion is satisfied and the evidence proves the real user-visible, integration, or contract surface works.
- Return REJECTION if any success criterion lacks evidence, any important scenario is untested, the diff introduces avoidable risk, the implementation drifts beyond scope, or the review packet is incomplete.
- "Looks good but..." is REJECTION.
- Do not accept explanations as evidence. Prefer command output, test results, screenshots, logs, or concrete code references.

Review dimensions:
1. Goal fit: did the work solve the actual request, including implied requirements?
2. Constraint compliance: did it respect stated constraints and existing project patterns?
3. Evidence quality: does verification prove behavior, not just absence of errors?
4. Regression risk: are adjacent surfaces, callers, data flows, or contracts affected?
5. Scope control: did the implementation add unnecessary behavior or abstractions?
6. Risk and maintainability: are there correctness, security, performance, or operability risks that should block completion?

Output exactly:

VERDICT: UNCONDITIONAL APPROVAL or REJECTION
CONFIDENCE: HIGH / MEDIUM / LOW
SUMMARY: 1-3 sentences

BLOCKING ISSUES:
For each blocker:
- Severity
- File/area
- Problem
- Evidence
- Required fix or required evidence

NON-BLOCKING NOTES:
Only include if useful. Keep short.
```

Append the full review packet and evidence paths after the assignment.

## Step 5: Apply The Binding Verdict

If the reviewer returns `UNCONDITIONAL APPROVAL`, copy the result to `reviewer-rounds/approval.md`.

If the reviewer is silent, times out, returns only an acknowledgement, or otherwise fails to produce a binding verdict, save an inconclusive round under `reviewer-rounds/round-N.md`:

```markdown
# Round N

VERDICT: INCONCLUSIVE
CONFIDENCE: LOW
SUMMARY: The reviewer did not return a binding `UNCONDITIONAL APPROVAL` or `REJECTION`. This is not approval.

BLOCKING ISSUES:
- Severity: Blocker
- File/area: review process
- Problem: No binding reviewer verdict was produced.
- Evidence: <timeout, silence, ack-only response, tool failure, or other concrete reason.>
- Required fix or required evidence: Resubmit the packet and obtain an explicit `UNCONDITIONAL APPROVAL` or `REJECTION`.

NON-BLOCKING NOTES:
- <Optional short note.>
```

If the reviewer returns `REJECTION`:

1. Save the reviewer output to `reviewer-rounds/round-N.md`.
2. Fix every blocking issue.
3. Re-run relevant verification.
4. Capture fresh evidence.
5. Update `review-packet.md` and `evidence.jsonl`.
6. Resubmit to the same reviewer when possible.
7. Loop until `UNCONDITIONAL APPROVAL`.

Do not treat silence, timeout, ack-only response, or inconclusive review as approval. If a reviewer finding seems factually wrong, verify it against the actual code or artifacts, then resubmit with evidence.

Reviewer agent, sub-agent, or tooling failures are process evidence. Record them in `reviewer-rounds/round-N.md`, `Known Risks And Skipped Checks`, `evidence.jsonl`, or task gate notes as appropriate. Do not treat a tooling failure as implementation approval or implementation rejection unless it directly prevents proving a success criterion.

## Final Report

Keep the final report short:

- final verdict
- reviewer confidence
- covered scope
- uncovered scope, if any
- evidence store path
- key evidence used
- review artifact commit decision
- blocking issues fixed, if any
- residual risk or skipped checks, if any
