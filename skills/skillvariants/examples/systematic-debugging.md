# SkillVariants study — systematic-debugging

Target: [obra/superpowers/skills/systematic-debugging/SKILL.md](https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md) (ref `main`)

## Corpus summary (deterministic)

- Candidate matches: 272
- Unique related variants: 175
- Exact copies collapsed: 0
- Mutation groups: 85
- Broad archetypes: compact-rewrite 34, workflow-specialization 30, routing-specialization 8, no-label 8, expanded-guidance 5

## Recurring adaptations

### 1. Add stop or escalation after repeated failed fixes

Observed across 9 mutation groups in 9 repositories.

**What changed.** An explicit trigger (usually three failed fix attempts) stops or escalates the debugging loop.

**Why it may matter.** (interpretation) May reflect a desire to bound an unbounded investigation loop so the agent reports back instead of thrashing.

**Tradeoff.** (interpretation) Tradeoff: a premature stop can cut off hard-but-solvable investigations.

Representative implementations:

- `aiskillstore/marketplace/skills/codingcossack/systematic-debugging/SKILL.md` — https://github.com/aiskillstore/marketplace/blob/main/skills/codingcossack/systematic-debugging/SKILL.md
- `RBraga01/a-team/skills/systematic-debugging/SKILL.md` — https://github.com/RBraga01/a-team/blob/main/skills/systematic-debugging/SKILL.md
- `jh941213/my-cc-harness/skills_en/systematic-debugging/SKILL.md` — https://github.com/jh941213/my-cc-harness/blob/main/skills_en/systematic-debugging/SKILL.md

### 2. Route completion verification to a separate skill

Observed across 5 mutation groups in 5 repositories.

**What changed.** Final completion/verification is delegated to a named verification skill instead of inline.

**Why it may matter.** (interpretation) May reflect separating root-cause finding from success-claiming.

**Tradeoff.** (interpretation) Tradeoff: adds a dependency on the verification skill.

Representative implementations:

- `coco-research/coco/skills/systematic-debugging/SKILL.md` — https://github.com/coco-research/coco/blob/main/skills/systematic-debugging/SKILL.md
- `coctostan/pi-superpowers-plus/skills/systematic-debugging/SKILL.md` — https://github.com/coctostan/pi-superpowers-plus/blob/main/skills/systematic-debugging/SKILL.md
- `bg-szy/TOP-SKILLS/skills/agent-skills/systematic-debugging/SKILL.md` — https://github.com/bg-szy/TOP-SKILLS/blob/master/skills/agent-skills/systematic-debugging/SKILL.md

### 3. Require reproduction before fixing

Observed across 5 mutation groups in 5 repositories.

**What changed.** Producing a reproduction becomes a gated step before any fix.

**Why it may matter.** (interpretation) May reflect that fixes without reproduction are the most common wasted effort.

**Tradeoff.** (interpretation) Tradeoff: some bugs are expensive to reproduce.

Representative implementations:

- `pratikrath126/ai-image-detector/.agent/kit-skills/systematic-debugging/SKILL.md` — https://github.com/pratikrath126/ai-image-detector/blob/main/.agent/kit-skills/systematic-debugging/SKILL.md
- `yimwoo/hotl-plugin/skills/systematic-debugging/SKILL.md` — https://github.com/yimwoo/hotl-plugin/blob/main/skills/systematic-debugging/SKILL.md
- `hnb-rabear/RCore/.agents/skills/systematic-debugging/SKILL.md` — https://github.com/hnb-rabear/RCore/blob/main/.agents/skills/systematic-debugging/SKILL.md

### 4. Add project-specific environment commands

Observed across 8 mutation groups in 8 repositories.

**What changed.** Adds commands, configuration, or environment checks specific to one repository or stack.

**Why it may matter.** (interpretation) Grounds the generic method in the actual repo tooling.

**Tradeoff.** (interpretation) Tradeoff: reduces portability.

Representative implementations:

- `eastreams/loong/skills/systematic-debugging/SKILL.md` — https://github.com/eastreams/loong/blob/rewrite/skills/systematic-debugging/SKILL.md
- `LiGoldragon/Mentci-AI/.pi/skills/systematic-debugging/SKILL.md` — https://github.com/LiGoldragon/Mentci-AI/blob/main/.pi/skills/systematic-debugging/SKILL.md
- `bg-szy/TOP-SKILLS/skills/agent-skills/systematic-debugging/SKILL.md` — https://github.com/bg-szy/TOP-SKILLS/blob/master/skills/agent-skills/systematic-debugging/SKILL.md

### 5. Add red-flags and anti-pattern guard

Observed across 4 mutation groups in 4 repositories.

**What changed.** Adds explicit violation indicators or anti-pattern lists.

**Why it may matter.** (interpretation) Lets a recursive agent catch itself mid-violation.

**Tradeoff.** (interpretation) Tradeoff: lists can go stale.

Representative implementations:

- `MadAppGang/claude-code/plugins/dev/skills/discipline/systematic-debugging/SKILL.md` — https://github.com/MadAppGang/claude-code/blob/main/plugins/dev/skills/discipline/systematic-debugging/SKILL.md
- `aiskillstore/marketplace/skills/codingcossack/systematic-debugging/SKILL.md` — https://github.com/aiskillstore/marketplace/blob/main/skills/codingcossack/systematic-debugging/SKILL.md
- `VidyaBodepudi/Code-Skills/skills/systematic-debugging/SKILL.md` — https://github.com/VidyaBodepudi/Code-Skills/blob/main/skills/systematic-debugging/SKILL.md

## Notable one-off adaptations

Several groups implement unique changes that do not recur across families; the full group list with per-group source links is in the evidence payload (`*-evidence.json`).

## Caveats

- GitHub code search is not a complete census; counts are a floor.
- Recurrence is not quality; motifs are observations, not recommendations.
- No ancestry is claimed; identical hashes prove identical bytes only.
- Archetypes and motifs are heuristic descriptive categories, not a formal taxonomy.
