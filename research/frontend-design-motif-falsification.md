# Frontend Design — Motif Falsification

**Family verdict: `MOTIF_STRONG`** (4 STRONG motifs)

## 1. Corpus summary

| Measure | Value |
|---|---|
| Candidates | 300 fetched (3 pages of code search) |
| Unique related variants | 189 |
| Mutation groups | 68 |
| Broad archetypes | workflow 33, compact-rewrite 14, routing 9, no-label 6, expanded 4, body-copy 1, wrapper 1 |
| Exact copies | 12 collapsed |

Reference: `anthropics/skills:skills/frontend-design/SKILL.md`.
Notably this family's anchor examples (PilotDeck compact rewrite,
qq-music-api wrapper) exist but were treated as anchors only, and the
Anti-slop template lineage (G2 cluster: 44 files / 110 occurrences, plus
G3/G7/G16/G21/G31 micro-clones) is a **propagation family, not a motif** —
it was coded as `wrapped-template-rewrite` and correctly FAILED recurrence
(worth YES = 0/2).

## 2. Annotation method

Identical flow as the systematic-debugging experiment:
`run_family.py` → one row per group (signals + added/removed excerpts +
direct SKILL.md URL) → human review bundle (`frontend-design-review-bundle.txt`)
→ coding per group (meaningful / worth_reviewing / up to 3 concrete-action
motif labels) → THEN consolidation and aggregation (`annotate_families.py`).
No family-specific hard-coded motif rules; no tuning of thresholds.

## 3. Meaningful-change counts

- meaningful = YES: 42
- meaningful = PARTIAL: 9
- meaningful = NO: 17

## 4. Candidate motifs

13 canonical labels after consolidation. The most frequent cluster is the
anti-slop template rewrite lineage (propagation, coded separately).

## 5. Recurring motifs (≥3 groups / ≥3 repos, no repo >50%)

| Motif | Groups | Repos | Worth=YES |
|---|---:|---:|---:|
| add framework-specific design rules | 5 | 5 | 5/5 |
| add evaluation-or-review gate | 5 | 5 | 4/5 |
| add contract-scope-or-output gates | 5 | 5 | 3/5 |
| add project-specific rules | 3 | 3 | 2/3 |
| (wrapped template rewrite — propagation) | 2 | 2 | 0/2 FAIL |

## 6. Strong vs weak motifs

### STRONG (4)

1. **add framework-specific design rules** — e.g.
   `OpenBMB/PilotDeck` no; actual members: `studio-jami/jami-studio` (shadcn/ui
   rules), `Everfern-AI/Everfern` (React/Next.js sections), `mrobbys`→no;
   `roerohan/skills` (React decision tree + 60-30-10), `YosemiteCrew`
   (design tokens + Tailwind), `duyet/skills` (stack priority ordering).
2. **add evaluation-or-review gate** — `rongxinzy/RongxinAI` (evaluation suite
   + delivery gate), `byerlikaya/claude-starter-kit` (ordered levers +
   checklist + invariant rules), `zszz3/AgentRecall` (verify + visual
   discipline + output), `OpenBMB/PilotDeck` (review checklist + migration
   note), `mohitagw15856` (design-system-first + quality checks).
3. **add contract-scope-or-output gates** — `samilozturk/agentlint`
   (when-to-use/scope/included-excluded/inputs),
   `ceilf6/FrontAgent` (trigger/do-not-use/output contract/guardrails),
   `dlwlgus9125/EZPowers` (machine-readable DESIGN.md before implementation),
   `dawsonblock` (definition/constraint/implement/refine),
   `benshapyro` (pre-implementation planning).
4. **add project-specific rules** — `quocthinhthan/Portfolio`
   (PROJECT_CONTEXT.md + Vietnamese/English site),
   `pavanchanduri/expense-tracker` (Spendly Flask/Jinja/Lucide design
   language), `tschuehly/lexware` (mobile-first + Safari + design-system
   doc link).

Worth-reviewing majority: 4/5, 4/5, 3/5, 2/3 — all pass the >50% bar.

### WEAK (recurring but maintenance/cosmetic)

- `wrapped-template-rewrite` — the dominant anti-slop clone lineage;
  0/2 worth=YES by representative coding.
- `add-domain-specific-design-rules` (2 groups: data-viz, finance) — real,
  below recurrence floor, and overlapping with project-specific.

## 7. Best developer-useful examples

- `duyet/skills` — tech-stack priority ordering (the skill tells the agent
  which UI stack to prefer before designing).
- `byerlikaya/claude-starter-kit` — six levers ordered by impact + invariant
  rules + context-budget-aware listing comment (an actual engineering
  constraint authored into the skill body).
- `dlwlgus9125/EZPowers` — design contract as a machine-readable `DESIGN.md`
  produced *before* implementation ("do not implement product UI code").
- `YosemiteCrew` — "Reuse Before Creating" + design tokens + class-ordering
  convention: a real design-system discipline translated into agent rules.

## 8. Propagation / template caveats

- The anti-slop lineage (44 member group + several micro-groups) is the
  single largest template-propagation cluster; it was explicitly excluded
  and is not counted toward any motif.
- `diegosouzapw/awesome-omni-skills` and `gabrielmoreira`-style mirror repos
  appear as intake copies (packaging + routing headers) — coded as
  repeated-publisher artifact, checked by max-share rule (all ≤33%).

## 9. Strongest counterexample

`add-evaluation-or-review-gate` on inspection is partly
**checklist-carbohydrate**: `julianoczkowski`, `KpG782`-style external
checklists inflate the appearance of a review gate without changing agent
behavior. The genuinely useful members are the ones that *order* work
(levers, verify-before-output) rather than merely listing criteria. This is
the family's clearest near-miss: frequency is driven by a shared template of
"guidelines + review checklist", not by independent design choice.

## 10. Family verdict

**MOTIF_STRONG** — 4 STRONG motifs despite the family being dominated by a
single template-propagation lineage. The motif signals are less
methodology-branded than systematic-debugging's (they are engineer-side
practices: framework/stack rules, review gates, contracts, project rules)
but they are concrete, recurring, and majority worth reviewing.

Evidence: `research/evidence-motifs/frontend-design/` (worksheet, records,
review bundle) and `annotate_families.py` (reproducible coding + aggregation).
