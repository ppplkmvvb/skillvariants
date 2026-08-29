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

## Prerequisites & invocation rule

```bash
uvx skillvariants --help        # or: pipx install skillvariants
```

**Invocation rule:** if `skillvariants` is available on PATH, call it
directly; otherwise use `uvx skillvariants ...`. The examples below use the
`uvx` form because it works without installation.

GitHub authentication is required for code search: `GITHUB_TOKEN` env var or
`gh auth login`.

## Workflow (follow in order)

1. **Collect evidence deterministically.** Run:

   ```bash
   uvx skillvariants evidence <SKILL.md-url> --json
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

5. **Consolidate by behavior equivalence, not topic similarity.** After all
   groups are labeled, merge proposed motifs ONLY when every supporting
   group can be truthfully described by the same concrete behavioral
   invariant — never because they are about the same general idea. Each
   canonical motif must carry:

   - one strict invariant sentence, and
   - a behavior signature: `trigger`, `action`, `object`, `outcome`.

   VALID merge: "stop after 3 failed fixes" + "escalate after repeated
   failed attempts" (one invariant: stop/escalation triggered by repeated
   failure). INVALID merge: "add review checklist" + "require DESIGN.md
   before implementation" (both about discipline, but different behaviors —
   split them).

6. **Verify every supporting group, then let deterministic counts establish
   recurrence.** Re-check each supporting group against the invariant
   (YES / NO / UNCERTAIN); NO and UNCERTAIN groups are removed from
   recurrence counting. If more than 20% of a cluster's groups are NO or
   UNCERTAIN, the cluster is UNSTABLE: split it once along behavior lines
   or omit it — never broaden the invariant to rescue it. A motif is
   recurring only when >= 3 verified-YES groups from >= 3 repositories with
   no single repository providing more than half the groups, computed by
   deterministic code, not by the model. Use the wording:

   > Observed across 6 mutation groups in 6 repositories.

   Never say "common", "widely adopted", or "independently invented".

7. **Present recurring motifs with source links.** For each motif: what
   changed, why it may matter (labeled as interpretation), and 3+
   representative implementations as `repo/path — direct_skill_url`.

8. **Distinguish observation from interpretation.** Three levels, never
   collapsed: (a) observed fact with counts, (b) interpretation ("this may
   reflect a desire to ..."), (c) user-specific suggestion — only when asked.

9. **Compare representative variants when useful.** Use
   `uvx skillvariants compare <target-url> <variant-url> --json` for a
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

Consolidation discipline in one line: PASS A is independent per group; PASS B clusters by behavior equivalence; every motif has one strict invariant; every supporting group is re-verified; uncertain groups do not count; recurrence comes from deterministic code; broad or unstable clusters are omitted, never rescued.

Deep references: [evidence-schema.md](references/evidence-schema.md) and
[interpretation-rules.md](references/interpretation-rules.md). A worked
example is in [examples/systematic-debugging.md](examples/systematic-debugging.md).
