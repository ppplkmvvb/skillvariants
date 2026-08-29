---
name: skillvariants
description: Study how a public Agent Skill has been adapted across GitHub using deterministic SkillVariants evidence, real source links, and semantic motif analysis. Use when the user asks how a skill has changed, which variants exist, what recurring adaptations look like, or whether a pattern might fit their own skill.
---

# SkillVariants — evidence-backed skill-variant studies

SkillVariants Core (the `skillvariants` CLI) is the **authoritative evidence
engine and study runtime**: it discovers related `SKILL.md` files on GitHub,
collapses copies, groups near-clones, batches semantic work, validates your
submissions, enforces the consolidation guardrail, and computes recurrence.
You are the **semantic analyst**: you perform exactly the task the runtime
returns, then submit the result. You never manage study state yourself.

## Prerequisites & invocation rule

```bash
uvx skillvariants --help        # or: pipx install skillvariants
```

**Invocation rule:** if `skillvariants` is available on PATH, call it
directly; otherwise use `uvx skillvariants ...`. The examples below use the
`uvx` form because it works without installation.

GitHub authentication is required for code search: `GITHUB_TOKEN` env var or
`gh auth login`.

## Workflow (six steps, loop-driven)

1. **Start or resume a study**

   ```bash
   uvx skillvariants study-start <SKILL.md-url> --json
   ```

   Returns `study_id` and whether an existing study was resumed.

2. **Call study-next**

   ```bash
   uvx skillvariants study-next <study-id> --json
   ```

   Returns exactly one task: `PASS_A_BATCH`, `PASS_B_CONSOLIDATE`,
   `VERIFY_MOTIF`, `FINAL_REPORT`, or `COMPLETE`.

3. **Perform exactly the returned task.**

   - `PASS_A_BATCH`: for each group, decide
     `meaningful_behavior_change` (YES/PARTIAL/NO) and propose 0-3 concrete
     action motifs. Each motif needs an `action`, one strict `invariant`
     sentence, and a `behavior_signature`
     (`trigger`/`action`/`object`/`outcome`). Analyze groups independently.
     If excerpts are insufficient, set `needs_source_escalation: true` with a
     `reason` and use the provided `compare_command` or `direct_skill_url`.
   - `PASS_B_CONSOLIDATE`: cluster the proposed motif actions by **behavior
     equivalence, not topic similarity**. Every supporting group must be
     truthfully described by the same behavioral invariant. One strict
     invariant + behavior signature per canonical motif; list rejected
     near-misses. Do not compute recurrence — the engine owns counts.
   - `VERIFY_MOTIF`: for each group decide YES/NO/UNCERTAIN against the
     motif's invariant. UNCERTAIN groups are excluded from recurrence.
   - `FINAL_REPORT`: write `report_md` with the required sections
     (Target Skill / Corpus summary / Recurring adaptations / Notable
     one-offs / Caveats) using ONLY the accepted motifs provided.

4. **Submit the result.**

   ```bash
   uvx skillvariants study-submit <study-id> <task-result.json>
   ```

   The runtime validates schema, ids, enums, and group membership, then
   advances state. Identical resubmissions are idempotent; conflicting ones
   are rejected without advancing.

5. **Repeat from step 2 until the task type is `COMPLETE`.**

6. **Present the report.** Read
   `.skillvariants/studies/<study-id>/report.md` (or run
   `uvx skillvariants study-report <study-id> --json`) and answer the user
   with the accepted motifs, counts, and source links.

## Interpretation discipline (never collapse these levels)

1. **Observed fact** — "Observed across 6 mutation groups in 6 repositories."
2. **Interpretation** — "This may reflect a desire to prevent implementation
   before explicit design approval."
3. **User-specific suggestion** — only when explicitly asked, and only after
   reading the user's actual Skill.

## Hard rules

- Never claim ancestry ("copied from", "original", "forked from").
- Never treat frequency as quality; a frequent motif can be shallow.
- Never fabricate or guess a URL; use `direct_skill_url` from the payload.
- Never present project-specific adaptations as general patterns.
- Never merge motifs by topic; merge only by behavior equivalence under one
  strict invariant, and split clusters that mix behaviors.
- Never broaden an invariant to rescue an unstable cluster — omit it.
- Never compute or present recurrence counts yourself; quote the runtime.
- Never modify the user's Skill files; this skill is read-only analysis.

Deep references: [evidence-schema.md](references/evidence-schema.md),
[interpretation-rules.md](references/interpretation-rules.md). Worked
example: [examples/systematic-debugging.md](examples/systematic-debugging.md).
