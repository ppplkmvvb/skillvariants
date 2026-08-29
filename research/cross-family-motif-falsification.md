# Cross-Family Motif Falsification — Final Report

**Cross-family verdict: `MOTIF_EXPLORER_GO`**

The motif depth first observed in `systematic-debugging` generalizes. Both
new families are `MOTIF_STRONG` (4 and 6 STRONG motifs). The question asked
by this experiment — whether Agent Skill variants consistently contain
concrete, recurring, developer-useful adaptation motifs across different
domains — is answered *yes* by corpus evidence, with specific caveats below.

## Final decision question (section 14)

> Across `systematic-debugging`, `frontend-design`, and `brainstorming`, is
> there enough evidence that Agent Skill variants contain recurring, concrete,
> developer-useful adaptation motifs to justify productizing a general motif
> explorer?

**Answer: YES.** 4 (FD) + 6 (BS) new STRONG motifs, plus the prior SD
findings. The motifs generalize across domains in *kind* — they are process
governance (hard gates, handoffs, stop conditions), engineering discipline
(framework rules, review gates, contracts), and environment/project adaption
— and they persist across all three families even after excluding the
dominant template-propagation lineages, which were coded separately and
consistently failed the quality bar (0/2 worth=YES in each family).

## Cross-family table (section 10)

| Family | Mutation groups | Recurring motifs | Strong motifs | Family verdict |
|---|---:|---:|---:|---|
| systematic-debugging (prior baseline) | 85 | 11 | 5* | DEPTH_PARTIAL‡ |
| frontend-design | 68 | 4 | 4 | **MOTIF_STRONG** |
| brainstorming | 90 | 8 | 6 | **MOTIF_STRONG** |

\* Prior experiment counted all items meeting the recurrence threshold as
"qualifying" and rated 9/11 above the DEPTH_GO quality bar; the SD depth
report's verdict was DEPTH_PARTIAL for reasons of semantic-consistency (C)
and majority-worth (D), which are exactly the gates this experiment applied
to the new families via the STRONG/WEAK split.

‡ SD's PARTIAL verdict and this experiment's STRONG verdicts are consistent:
this experiment's STRONG gate (recurrence + majority worth-reviewing) is the
*positive half* of SD's D criteria; SD additionally penalized itself on
consistency and on the two motifs that are maintainer-caliber.

## Per-family comparison

| | SD | FD | BS |
|---|---|---|---|
| Groups reviewed | 85 | 68 | 90 |
| Meaningful = YES | 71 (84%) | 42 (62%) | 76 (84%) |
| Worth = YES rate | 29/85 (34%) | 26/68 (38%) | 38/90 (42%) |
| Recurring motifs | 11 | 4 | 8 |
| STRONG | 5 (WEAK severity on 6) | 4 | 6 |
| Dominant template lineage excluded | yes (G1: 41 members) | yes (44-member anti-slop family) | yes (29 + 22 member lineages) |
| Recurrence dominated by one repo? | no (max 33%) | no (max 33%) | no (max 33%) |

## The motifs by domain

**systematic-debugging (baseline, not re-run):**
add stop-or-escalation after repeated failed fixes; preserve root-cause-first
while composing; route completion verification to separate skill; add
red-flags/anti-pattern guard; add one-hypothesis-at-a-time.

**frontend-design (new):**
- add framework-specific design rules (stack/token/UI-library priorities)
- add evaluation-or-review gate (levers, verify-before-output, checklist)
- add contract-scope-or-output gates (scope/guardrails/DESIGN.md-before-code)
- add project-specific rules (project-context loading, design language)

**brainstorming (new):**
- add explicit hard-gate implementation lock (never-code-before-approval)
- add ownership-or-handoff boundary (responsibility statements, worktree handoff)
- add stop-or-fallback condition (stop conditions, red-flag stop, phase BLOCK gates)
- add traceability-or-spec-output rule (B#/F# traceability, problem/solution/user-stories)
- add environment-or-availability guard (workflow-mode guard, prompt-prefix availability)
- add greenfield-vs-existing path split (greenfield bootstrap vs existing codebase)

The surprising **cross-family overlap**: "stop/fallback after repeated
failure" and "never implement before an explicit gate" appear in SD
(repeated-fixes escape hatch) and BS (hard-gate implementation lock,
stop-or-fallback) as structurally identical *process governance* adaptations
authored by different people. This is the strongest generalizability evidence
the experiment produced.

## Propagation / independence (section 8)

- Both new families contain one or two dominant template lineages; each was
  excluded from motif counting (coded `wrapped-template-rewrite`, 0/2
  worth=YES). No STRONG motif derives primarily from a single near-copy
  cluster; each supporting group is an independent-file/near-copy group and
  no repo exceeds 33% share.
- We report recurrence in groups/repos terms ("observed across N distinct
  near-copy groups"), never "independently invented" or ancestry.

## Automatability (section 13, optional check)

For the 10 new STRONG motifs, deterministic detectability by the existing
feature system:

| Motif family | Detectability | Notes |
|---|---|---|
| hard-gate (BS) | EXISTING | "HARD-GATE"/"before approval" phrase + "never write code" — trivial regex; also ALL-CAPS rule intersection. |
| ownership/handoff (BS) | SMALL_DETECTOR | "owns"/"handoff"/"delegat" phrase + cross-skill ref delta. |
| stop/fallback (BS) | SMALL_DETECTOR | "stop condition"/"fallback"/"red flag" phrases. |
| traceability/spec-output (BS) | SMALL_DETECTOR | "traceab"/"B#"/"user stor" + design-doc output heading. |
| environmental guard (BS) | SMALL_DETECTOR | "workflow mode"/"only available"/"not to use". |
| greenfield split (BS) | SMALL_DETECTOR | "greenfield"/"existing codebase" heading. |
| framework-specific (FD) | SMALL_DETECTOR | known framework tokens (React/Next/Tailwind/shadcn) + design-rules heading. |
| evaluation/review gate (FD) | SMALL_DETECTOR | "evaluation"/"review checklist"/"verify"/"delivery gate" headings. |
| contract/scope gates (FD) | SMALL_DETECTOR | "scope"/"trigger"/"guardrail"/"design.md"/"output contract" headings. |
| project-specific (FD) | EXISTING | project-phrase regex already in feature system. |

All 10 are detectable with existing signals plus small generic phrase/heading
detectors; none requires LLMs or embeddings. The recurring, "worth reviewing"
motifs we surfaced are therefore also a cheap, deterministic layer.

## Caveats (section 9/7)

- The strongest counterexample overall is **questioning-protocol (BS)** and
  **review-checklist (FD)**: these are the "frequent but shallow" motifs —
  they passed recurrence but failed majority-worth. They would be the first
  place a naive frequency-based explorer would be wrong.
- The FD family is structurally dominated by a single template lineage; its
  STRONG count (4) is lower than BS despite more variants. Motif quality and
  variant quantity are anti-correlated here — worth noting for product design.
- This experiment did not modify the prior SD results or tune any threshold.

## Conclusion for SkillVariants

Productizing a **general motif explorer** is justified by corpus evidence:
a deterministic motif layer (existing features + 5-10 small detectors) can
surface concrete recurring adaptations in all three test families, with
recurrence + quality filtering preventing the fake-convergence trap seen in
cloning. This is not a recommendation system and does not infer ancestry.

**Verdict: `MOTIF_EXPLORER_GO`**

Per section 15, the next phase may be: deterministic motif layer + real
SKILL.md source links + compare + interactive Web explorer. It must not be
positioned as an automatic improvement recommender. STOP — no product
implementation in this run.
