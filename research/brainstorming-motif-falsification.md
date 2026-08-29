# Brainstorming — Motif Falsification

**Family verdict: `MOTIF_STRONG`** (6 STRONG motifs)

## 1. Corpus summary

| Measure | Value |
|---|---|
| Candidates | 300 fetched |
| Unique related variants | 199 |
| Mutation groups | 90 |
| Broad archetypes | workflow 38, compact-rewrite 33, routing 11, no-label 8 |
| Exact copies | 0 collapsed |

Reference: `obra/superpowers:skills/brainstorming/SKILL.md`.
Two large propagation clusters exist (a 29-member "Overview/Process/After
the Design" lineage and a 22-member "Checklist/Process Flow/The Process"
lineage, both ~55-63 occurrences). Both were coded as
`wrapped-template-rewrite` and FAILED recurrence (worth YES = 0/2) — by
design, not by accident.

## 2. Annotation method

Identical flow to the prior experiment and to frontend-design:
one row per mutation group from `run_family.py` (with direct SKILL.md URLs),
human review bundle `brainstorming-review-bundle.txt`, coding before
aggregation, then consolidation in `annotate_families.py`.

## 3. Meaningful-change counts

- meaningful = YES: 76
- meaningful = PARTIAL: 2
- meaningful = NO: 12

The highest meaningful-YES share of the three families (84%).

## 4. Candidate motifs

13 canonical labels. Most frequent were a family of
"gate/handoff" motifs (below) rather than one dominant template.

## 5. Recurring motifs (≥3 groups / ≥3 repos, no repo >50%)

| Motif | Groups | Repos | Worth=YES |
|---|---:|---:|---:|
| add questioning-or-interaction protocol | 7 | 7 | 3/7 |
| add ownership-or-handoff boundary | 6 | 6 | 6/6 |
| add explicit hard-gate implementation lock | 6 | 6 | 6/6 |
| add traceability-or-spec-output rule | 4 | 4 | 3/4 |
| add diverge/converge phase split | 4 | 4 | 2/4 |
| add environment-or-availability guard | 3 | 3 | 2/3 |
| add greenfield-vs-existing path split | 3 | 3 | 3/3 |
| add stop-or-fallback condition | 3 | 3 | 3/3 |

## 6. Strong vs weak motifs

### STRONG (6)

1. **add ownership-or-handoff boundary** — `mengsi16/plan-for-all` (what this
   skill owns + required output), `cheetahbyte/dotfiles` (affirmative
   "Brainstorming owns" + delegation),
   `doviettung96/apk-tool` (planner handoff), `coctostan/pi-superpowers-plus`
   (related-skills router), `Yassimba/loom` (what vs how split),
   `bharat3645/The-Ideal-Harness` (single-output handoff). 6/6 worth=YES.
2. **add explicit hard-gate implementation lock** —
   `ahippelainen/claude-loadout`, `jh941213/my-cc-harness`,
   `bharat3645`, `hnb-rabear/hnb-rabear.github.io`, `stvhay/pi-setup`,
   `MaxFerAlten/tenderclaw` — spelled `<HARD-GATE>`/never-code-before-approval.
   6/6 worth=YES.
3. **add stop-or-fallback condition** — `apenlor/opencode-expert-mode`
   (Stop Conditions + Fallbacks), `drbothen/vsdd-factory` (red flags →
   STOP), `majiayu000/.../arbiterforge` (phase gates BLOCK/STOP). 3/3 worth=YES.
4. **add traceability-or-spec-output rule** — `Allura-Ecosystem/Allura_Memory`
   (B#/F# traceability MANDATORY), `Vpr99` (problem/solution/user stories),
   `ericgandrade` (progress tracking), `qq1030655828` (restate goal + missing
   constraints). 3/4 worth=YES.
5. **add environment-or-availability guard** —
   `stefaniuk/loadout` (workflow-mode guard), `openteams-lab/openteams`
   (prompt-prefix availability), `itseffi/agentic-os` (when to use vs not).
   2/3 worth=YES.
6. **add greenfield-vs-existing path split** — `derHaken/SuperAntigravity`
   (Greenfield Projects), `kyaulabs/prism` (strict-greenfield bootstrap),
   `Benkapner` (working-in-existing-codebases). 3/3 worth=YES.

### WEAK (recurring but not majority-worth-reviewing)

- **add questioning-or-interaction protocol** (7 groups, only 3/7 worth=YES)
  — highly frequent (one-question-at-a-time / AskUserQuestion / 3-questions
  gate) but the implementations are mostly restatements of the reference's
  own "ask questions one at a time" wording; it fails the majority-worth bar.
- **add diverge/converge phase split** (4 groups, 2/4) — real but often a
  rename of the same process instead of a structural change.

## 7. Best developer-useful examples

- `mengsi16/plan-for-all` — the skill defines itself as "the
  customer-facing convergence layer" with an explicit needed-output; an
  unusually mature responsibility statement.
- `Allura-Ecosystem/Allura_Memory` — spec must trace to the Blueprint's
  B#/F# requirements; the closest thing to a requirements-traceability hook
  in any of the three families.
- `apenlor/opencode-expert-mode` — Stop Conditions + Fallbacks embedded in a
  brainstorming skill: the same escape-hatch pattern we found in
  systematic-debugging, independently re-authored.
- `cheetahbyte/dotfiles` — explicit delegation: "Brainstorming owns
  exploring the existing system... delegating user-owned decisions."

## 8. Propagation / template caveats

- Two large propagation lineages (29-member and 22-member clusters) were
  excluded from motifs after coding as template rewrites; they dominate
  occurrence counts (~118 of ~330 group occurrences) but contribute 0
  strong motifs.
- `diegosouzapw/awesome-omni-skills` intake-copy and `gabrielmoreira`
  mirror appear once each; no repo exceeds 33% share on any qualifying motif.

## 9. Strongest counterexample

`add questioning-or-interaction protocol` — the most "obviously recurring"
pattern (one-question-at-a-time, multiple-choice, AskUserQuestion) is also
the weakest STRONG candidate; it often reproduces the reference text's own
instruction. Frequency here does not equal design choice. This is the single
clearest demonstration of the anti-bias rule: had we ranked by frequency
first, this would be #1 and most of its examples would be nearly-copies.

## 10. Family verdict

**MOTIF_STRONG** — 6 STRONG motifs. The family's recurring adaptations are
characteristically *process-governance*: hard gates, handoff boundaries,
stop conditions, availability guards, traceability, and environment splits.
These are developer-actionable and (unlike SD) skew heavily toward
"worth reviewing = YES".

Evidence: `research/evidence-motifs/brainstorming/` (worksheet, records,
review bundle) and `annotate_families.py`.
