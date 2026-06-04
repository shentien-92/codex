---
name: grill-trellis
description: Grilling session that challenges your plan against the existing Trellis spec context, sharpens terminology, and records spec/ADR candidates as decisions crystallise. Use when user wants to stress-test a plan against their project's language and documented decisions.
---

<what-to-do>

Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

Ask the questions one at a time, waiting for feedback on each question before continuing.

When grilling the user, use the `question` tool whenever practical to present focused choices and improve the interaction experience.

If a question can be answered by exploring the codebase, explore the codebase instead.

</what-to-do>

<supporting-info>

## Domain awareness

During codebase exploration, also look for existing Trellis documentation:

### File structure

Trellis owns the project documentation context:

```
/
├── .trellis/
│   └── spec/
│       ├── context/
│       │   └── CONTEXT.md
│       └── adr/
│           ├── 0001-event-sourced-orders.md
│           └── 0002-postgres-for-write-model.md
└── src/
```

Do not look for or maintain a root `CONTEXT-MAP.md`. Trellis manages complex repositories through `.trellis/spec/` instead.

Create files lazily — only when you have something to write. If no `.trellis/spec/context/CONTEXT.md` exists, create one when the first term is resolved. If no `.trellis/spec/adr/` exists, create it when the first ADR is needed.

## During the session

### Challenge against the glossary

When the user uses a term that conflicts with the existing language in `.trellis/spec/context/CONTEXT.md`, call it out immediately. "Your glossary defines 'cancellation' as X, but you seem to mean Y — which is it?"

### Sharpen fuzzy language

When the user uses vague or overloaded terms, propose a precise canonical term. "You're saying 'account' — do you mean the Customer or the User? Those are different things."

### Discuss concrete scenarios

When domain relationships are being discussed, stress-test them with specific scenarios. Invent scenarios that probe edge cases and force the user to be precise about the boundaries between concepts.

### Cross-reference with code

When the user states how something works, check whether the code agrees. If you find a contradiction, surface it: "Your code cancels entire Orders, but you just said partial cancellation is possible — which is right?"

### Update CONTEXT.md inline

When a term is resolved, update `.trellis/spec/context/CONTEXT.md` right there. Don't batch these up — capture them as they happen. Use the format in [CONTEXT-FORMAT.md](./CONTEXT-FORMAT.md).

Don't couple `CONTEXT.md` to implementation details. Only include terms that are meaningful to domain experts.

### Offer ADRs sparingly

Treat ADR updates like spec updates: do not passively wait for the user to ask. When a decision appears likely to deserve an ADR, proactively ask the user with the `question` tool.

Only propose an ADR when all three are true:

1. **Hard to reverse** — the cost of changing your mind later is meaningful
2. **Surprising without context** — a future reader will wonder "why did they do it this way?"
3. **The result of a real trade-off** — there were genuine alternatives and you picked one for specific reasons

If any of the three is missing, skip the ADR. Use the format in [ADR-FORMAT.md](./ADR-FORMAT.md).

If you identify an ADR-worthy or spec-worthy event while writing a PRD, record it in `research/spec-candidates.md`. During finish, extract the relevant entries from that file to decide whether they should land in `.trellis/spec/`.

</supporting-info>
