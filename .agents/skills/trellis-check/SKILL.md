---
name: trellis-check
description: "Comprehensive quality verification: spec compliance, lint, type-check, tests, cross-layer data flow, code reuse, and consistency checks. Use when code is written and needs quality verification, before committing changes, or to catch context drift during long sessions."
---

# Code Quality Check

Comprehensive quality verification for recently written code. Combines spec compliance, cross-layer safety, and pre-commit checks.

---

## Step 1: Identify What Changed

```bash
git diff --name-only HEAD
git status
```

## Step 2: Read Task Artifacts and Applicable Specs

Read the current task artifacts in order:

- `prd.md`
- `design.md` if present
- `implement.md` if present
- `.trellis/spec/context/CONTEXT.md` when changed behavior or review criteria depend on project terminology
- `.trellis/spec/adr/` when the change touches architectural choices or trade-offs

```bash
python3 ./.trellis/scripts/get_context.py --mode packages
```

For each changed package/layer, read the spec index and follow its **Quality Check** section:

```bash
cat .trellis/spec/<package>/<layer>/index.md
```

Read the specific guideline files referenced — the index is a pointer, not the goal.

ADRs under `.trellis/spec/adr/` are optional, but the check should know they exist and inspect them when validating decisions that would be surprising without context.

## Step 3: Run Project Checks

Run the project's lint, type-check, and test commands. Fix any failures before proceeding.

## Step 4: Build PRD Coverage Matrix

Before the general quality checklist, extract the verifiable requirements from
`prd.md`:

- numbered or bulleted items under `Requirements`
- every checklist item under `Acceptance Criteria`
- any must-complete checklist or behavior from `design.md` / `implement.md`
  when present

Report a PRD coverage matrix with one row per item:

| Item | Status | Evidence |
| --- | --- | --- |
| AC-1: <original acceptance item> | pass / fail / not_verifiable | <file, test, command, screenshot, or reason> |

Rules:

- `pass` requires concrete evidence. Do not mark an item as passed from
  confidence alone.
- `fail` means the implementation is missing or wrong. Fix it when in scope,
  then rebuild the matrix.
- `not_verifiable` means the item cannot be proven from the available code,
  tests, commands, or manual evidence. Explain why and list it as residual
  risk.
- If any item remains `fail`, do not say the task is complete, all fixed, or
  has no remaining issues.
- If `prd.md` has no testable acceptance criteria, report that as a PRD quality
  problem and recommend returning to planning instead of inventing criteria.

## Step 5: Review Against Checklist

### Code Quality

- [ ] Linter passes?
- [ ] Type checker passes (if applicable)?
- [ ] Tests pass?
- [ ] No debug logging left in?
- [ ] No suppressed warnings or type-safety bypasses?

### Test Coverage

- [ ] New function → unit test added?
- [ ] Bug fix → regression test added?
- [ ] Changed behavior → existing tests updated?

### Spec Sync

- [ ] Does `.trellis/spec/` need updates? (new patterns, conventions, lessons learned)

> "If I fixed a bug or discovered something non-obvious, should I document it so future me won't hit the same issue?" → If YES, update the relevant spec doc.

## Step 6: Cross-Layer Dimensions (if applicable)

Skip this step if your change is confined to a single layer.

### A. Data Flow (changes touch 3+ layers)

- [ ] Read flow traces correctly: Storage → Service → API → UI
- [ ] Write flow traces correctly: UI → API → Service → Storage
- [ ] Types/schemas correctly passed between layers?
- [ ] Errors properly propagated to caller?

### B. Code Reuse (modifying constants, creating utilities)

- [ ] Searched for existing similar code before creating new?
  ```bash
  grep -r "pattern" src/
  ```
- [ ] If 2+ places define same value → extracted to shared constant?
- [ ] After batch modification, all occurrences updated?

### C. Import/Dependency (creating new files)

- [ ] Correct import paths (relative vs absolute)?
- [ ] No circular dependencies?

### D. Same-Layer Consistency

- [ ] Other places using the same concept are consistent?

---

## Step 7: Report and Fix

Report PRD coverage first, then violations found and fixed. Re-run project
checks after fixes.
