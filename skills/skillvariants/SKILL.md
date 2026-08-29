---
name: skillvariants
description: Study how a public Agent Skill has been adapted across GitHub using deterministic SkillVariants evidence, real source links, and semantic motif analysis. Use when the user asks how a skill has changed, which variants exist, what recurring adaptations look like, or whether a pattern might fit their own skill.
---

# SkillVariants — evidence-backed skill-variant studies

SkillVariants Core (the `skillvariants` CLI) is the **authoritative
evidence engine**: it discovers related `SKILL.md` files on GitHub, collapses
copies, groups near-clones, and produces structural diffs with source links.
You are the **semantic analyst**: you interpret that evidence into concrete,
recurring mutation motifs. You never invent facts the engine did not produce.

## Prerequisites

```bash
uvx skillvariants --help        # or: pipx install skillvariants
```

GitHub authentication is required for code search: `GITHUB_TOKEN` env var or
`gh auth login`.

## Workflow (follow in order)

1. **Collect evidence deterministically.** Run:

   ```bash
   skillvariants evidence <SKILL.md-url> --json
   ```

   Everything you need is in the JSON: `target`, `summary` (counts only),
   and `groups[]` (one per mutation group, each with a `direct_skill_url`,
   `structural_signals`, and short `added_excerpt`/`removed_excerpt`).

2. **Read the summary first.** Report candidate count, unique related
   variants, exact-copy count, and mutation-group count as plain facts.

3. **Analyze groups independently.** For each group decide: is there a
   meaningful behavioral change (YES/PARTIAL/NO)? Do not look at other
   groups while deciding. Skip groups with no meaningful change.

4. **Identify concrete action motifs.** Phrase each motif as a concrete
   action: "Add ...", "Remove ...", "Route ...", "Require ...",
   "Preserve ... while ...". Never use vague labels ("shorter", "expanded",
   "better workflow"). A group may have zero motifs.

5. **Consolidate only under strict invariants.** After all groups are
   labeled, merge proposed motifs that are semantically equivalent and write
   ONE invariant sentence per canonical motif, e.g.:

   > Introduces an explicit termination or escalation condition triggered by
   > repeated failed attempts.

   Then re-check EVERY supporting group against that invariant. Reject
   near-misses. If a cluster mixes several ideas, split it.

6. **Let deterministic counts establish recurrence.** Count distinct
   mutation groups and distinct repositories from the evidence payload. A
   motif is recurring only at >= 3 groups AND >= 3 repositories with no
   single repository providing more than half the groups. Use the wording:

   > Observed across 6 mutation groups in 6 repositories.

   Never say "common", "widely adopted", or "independently invented".

7. **Present recurring motifs with source links.** For each motif: what
   changed, why it may matter (labeled as interpretation), and 3+
   representative implementations as `repo/path — direct_skill_url`.

8. **Distinguish observation from interpretation.** Three levels, never
   collapsed: (a) observed fact with counts, (b) interpretation ("this may
   reflect a desire to ..."), (c) user-specific suggestion — only when asked.

9. **Compare representative variants when useful.** Use
   `skillvariants compare <target-url> <variant-url> --json` for a
   structural diff of two specific files.

10. **Only discuss applicability to the user's own Skill when explicitly
    asked**, and only after reading their actual Skill content.

## Output shape

```text
Target Skill

Corpus summary

Recurring adaptations

1. <motif>
   Observed across N groups / N repositories
   What changed
   Why it may matter        (interpretation)
   Tradeoff                 (interpretation)
   Representative implementations:
   - repo/path — https://github.com/...
```

No scores. No "best variant". No "best practices".

## Hard rules

- Never claim ancestry ("copied from", "original", "forked from") — hashes
  prove identical bytes, nothing more.
- Never treat frequency as quality; a frequent motif can be shallow.
- Never fabricate or guess a URL; use `direct_skill_url` from the payload.
- Never present project-specific adaptations as general patterns.
- Never modify the user's Skill files; this skill is read-only analysis.

Deep references: [evidence-schema.md](references/evidence-schema.md) and
[interpretation-rules.md](references/interpretation-rules.md). A worked
example is in [examples/systematic-debugging.md](examples/systematic-debugging.md).
