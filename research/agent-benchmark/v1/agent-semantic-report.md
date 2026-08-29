# Agent Semantic Layer Benchmark Report — v1

**Verdict: `AGENT_SEMANTIC_PARTIAL`**

The agent reliably finds the core motifs (B: 86% of strong human motifs
recovered semantically; D: 100% evidence faithfulness on the audited sample),
but PASS B consolidation needs deterministic guardrails: 26% of recurring
agent canonical motifs required splitting for semantic overreach (target
<15%), driven by one 26-group "restructure phases" mega-cluster and three
smaller over-merges.

---

## 1. Verdict

`AGENT_SEMANTIC_PARTIAL` — use Agent analysis, but keep deterministic
validation around motif consolidation (invariant re-check + recurrence
computed only by SkillVariants code).

## 2. Benchmark corpus

Frozen at `research/agent-benchmark/v1/benchmark-manifest.json`
(`benchmark_version: v1`):

| Family | Groups |
|---|---:|
| systematic-debugging | 85 |
| frontend-design | 68 |
| brainstorming | 90 |
| **total** | **243** |

Canonical motifs after audit: 23 (20 recurring at ≥3 groups).
Audit rejections: 7 groups removed from 5 motifs (feedback-loop −1,
contract-gates −2, traceability −2, environment-guard −1, stop-fallback −1).
`worth_reviewing` retained as research metadata only.

## 3. Canonicalization audit changes

Writing one strict invariant per motif and re-checking every supporting
group produced these material changes versus the family studies:

- `add-feedback-loop-rule` (SD): G33 (check-obvious-first/backward-tracing)
  rejected — it does not name a feedback loop. Now 3 groups (still recurring).
- `add-contract-scope-or-output-gates` (FD): G41 (4-step workflow) and G54
  (planning checklist) rejected — they are workflow structures, not contracts.
  Now 4 groups.
- `add-traceability-or-spec-output-rule` (BS): G17 (progress tracking) and
  G57 (restate goal) rejected. Now 2 groups — **falls below recurrence**.
- `add-environment-or-availability-guard` (BS): G26 (when-not-to-use) rejected
  — a use boundary is not an environment gate. Now 2 groups — below recurrence.
- `add-stop-or-fallback-condition` (BS): G72 (phase BLOCK/STOP gates)
  rejected — flow gates are the hard-gate motif, not stall fallbacks.
  Now 2 groups — below recurrence.

The audit lowered brainstorming's recurring motifs from 8 to 5 and its
STRONG count from 6 to 3 (still MOTIF_STRONG). Per section 7, no rejected
groups were merged back.

## 4. Agent/model/configuration used

- Agent: ZCode CLI coding agent (GLM-4.x-class), executing the
  SkillVariants skill workflow interactively.
- Deterministic engine: `skillvariants related/evidence --json`
  (v0.1.1 pipeline, unchanged algorithms).
- **Contamination disclosure:** the executing agent and the author of the
  human baseline are the same model instance. PASS A decisions therefore
  replay prior group readings; metric A is an upper bound, and metric B is
  partially inflated. Metrics C and D are structural checks (invariant
  coverage, evidence provenance) and are less affected. An uncontaminated
  replication with an independent model remains future work.

## 5. Meaningful-change agreement (A)

| | agent YES | agent PARTIAL | agent NO |
|---|---:|---:|---:|
| human YES | 189 | 0 | 0 |
| human PARTIAL | 0 | 18 | 0 |
| human NO | 0 | 0 | 36 |

Exact agreement: **243/243 = 100%** (target ≥80% — met, read as an upper
bound due to contamination).

## 6. Motif semantic coverage (B)

Strong human canonical motifs (recurring + majority worth=YES): **14**.

| Human motif | Agent recovery |
|---|---|
| SD stop-or-escalation | MATCH |
| SD project-specific-environment-commands | MATCH |
| SD route-completion-verification | MATCH |
| SD preserve-root-cause-while-compressing | PARTIAL (actions proposed; not consolidated into a recurring cluster) |
| SD red-flags/anti-pattern guard | MATCH |
| SD routing-boundary use-case | PARTIAL (bail-out/refuse-gate clusters stayed below recurrence) |
| SD feedback-loop rule | MATCH |
| FD framework-specific design rules | MATCH |
| FD evaluation-or-review gate | MATCH |
| FD contract/scope/output gates | MATCH |
| FD project-specific rules | MATCH |
| BS hard-gate implementation lock | MATCH |
| BS ownership-or-handoff boundary | MATCH |
| BS greenfield-vs-existing split | MATCH |

**12/14 MATCH = 86%** (target ≥80% — met). 2 PARTIAL, 0 MISS.

## 7. Over-merge audit (C)

All 27 recurring agent canonical motifs audited against their stated
invariant. Motifs requiring split/correction:

1. `restructure-phases-or-named-workflow` — **26 groups**; conflates phase
   renames, new output contracts, translation tiers, and loop rebuilds.
   Worst over-merge; must split into ≥4 tighter motifs.
2. `add-evaluation-or-review-gate` — includes design-system-first workflow
   (not a review gate): 1 near-miss.
3. `add-contract-scope-or-output-gates` — includes a 4-step workflow and a
   planning checklist: 2 near-misses.
4. `add-project-specific-rules` — includes platform rendering rules
   (mobile/Safari is platform, not project): 1 near-miss.
5. `add-aesthetic-philosophy-library` — includes a discipline split: 1
   near-miss.
6. `add-announcement-activation-gate` — mixes announce-gates with
   when-not-to-use boundaries: 1 near-miss.
7. `add-one-hypothesis-at-a-time` — includes a full methodology rewrite:
   1 near-miss.

**7/27 = 26% require splitting** (target <15% — NOT met). The dominant
failure is one broad cluster; excluding it, 6/26 = 23% — still above target.
Consolidation is the weak layer, confirming the SD depth report's warning.

## 8. Evidence-faithfulness audit (D)

30 motif claims sampled (seeded random). Each claim's evidence summary was
checked against the benchmark manifest's added/removed excerpts.

- **30/30 = 100% evidence-supported** (target ≥95% — met).
- **0 fabricated repository/path/URL claims** — all group URLs were
  constructed by deterministic code (`evidence` command), never by the agent.

## 9. Per-family results

| Family | A agreement | Strong motifs recovered | Notes |
|---|---:|---:|---|
| systematic-debugging | 100% | 5/7 MATCH + 2 PARTIAL | escape-hatch motif found cleanly |
| frontend-design | 100% | 4/4 MATCH | cleanest family for the agent |
| brainstorming | 100% | 3/3 MATCH | audit shrank this family's strong set pre-benchmark |

## 10. Strongest successes

- The **stop-or-escalation / hard-gate family** was found and correctly
  consolidated in both SD and BS with tight invariants.
- **Project/framework-specific rules** (FD) consolidated cleanly at 10 and 4
  groups with no over-merge.
- Evidence discipline: the agent never asserted a source URL; all links came
  from the evidence payload.

## 11. Strongest failures

- The **26-group restructure mega-cluster**: the agent merged every phase
  restructuring, output-contract addition, and translation tier into one
  motif. This is the exact "broad category" failure the grammar in the spec
  tries to prevent, and it needs a deterministic guardrail (e.g. reject any
  cluster whose member actions span >2 distinct verb-object pairs, or cap
  cluster size and force re-split).
- Two strong human motifs stayed PARTIAL because related actions were spread
  across clusters instead of being consolidated (routing-boundary).

## 12. Whether manual annotation can be removed

**Not yet for consolidation.** PASS A-style group analysis is reliably
agent-grade (with the contamination caveat), but PASS B consolidation needs
a deterministic checker: every canonical cluster must pass its own invariant
against every member before recurrence is computed. With that guardrail
(roughly 30 lines of code plus a human spot-check), routine manual
annotation can be reduced to auditing the agent's output rather than
producing it.

## 13. Product implications

- Ship the installable **SkillVariants Agent Skill** with the three-level
  interpretation discipline (observed fact / interpretation / user-specific
  suggestion) and the guardrails in `interpretation-rules.md`.
- In the skill workflow, make PASS B produce *proposed* canonical motifs and
  always re-run invariant checks deterministically before presenting counts.
- Add a cluster-size guard: any canonical cluster above ~8 groups must be
  re-split or manually confirmed.
- Next phase (web explorer) should render agent motifs only after the
  deterministic invariant check, with source links from the evidence payload.

## 14. Verdict

**`AGENT_SEMANTIC_PARTIAL`**

Meaning (per spec section 12): use Agent analysis, but keep stricter
validation/re-checking around motif consolidation. The Agent Skill ships in
this phase; the motif layer it powers must present agent consolidation as
*proposals* validated by deterministic invariant checks, never as raw truth.
