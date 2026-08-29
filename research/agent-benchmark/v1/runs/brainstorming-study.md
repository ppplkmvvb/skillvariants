# SkillVariants study — brainstorming

Target: [obra/superpowers/skills/brainstorming/SKILL.md](https://github.com/obra/superpowers/blob/main/skills/brainstorming/SKILL.md) (ref `main`)

## Corpus summary (deterministic)

- Candidate matches: 300
- Unique related variants: 199
- Exact copies collapsed: 0
- Mutation groups: 90
- Broad archetypes: workflow-specialization 38, compact-rewrite 33, routing-specialization 11, no-label 8

## Recurring adaptations

### 1. Add explicit hard-gate implementation lock

Observed across 6 mutation groups in 6 repositories.

**What changed.** An unavoidable prohibition on writing code before design approval.

**Why it may matter.** (interpretation) The most common failure is skipping ideation entirely.

**Tradeoff.** (interpretation) Tradeoff: rigid gates can block trivial changes.

Representative implementations:

- `ahippelainen/claude-loadout/claude/skills/brainstorming/SKILL.md` — https://github.com/ahippelainen/claude-loadout/blob/main/claude/skills/brainstorming/SKILL.md
- `jh941213/my-cc-harness/skills_en/brainstorming/SKILL.md` — https://github.com/jh941213/my-cc-harness/blob/main/skills_en/brainstorming/SKILL.md
- `bharat3645/The-Ideal-Harness/skills/brainstorming/SKILL.md` — https://github.com/bharat3645/The-Ideal-Harness/blob/main/skills/brainstorming/SKILL.md

### 2. Add ownership-or-handoff boundary

Observed across 6 mutation groups in 6 repositories.

**What changed.** States what the skill owns vs delegates, or where it hands off.

**Why it may matter.** (interpretation) Multi-skill pipelines need clear stage boundaries.

**Tradeoff.** (interpretation) Tradeoff: requires downstream stages to exist.

Representative implementations:

- `doviettung96/apk-tool/.codex/skills/brainstorming/SKILL.md` — https://github.com/doviettung96/apk-tool/blob/main/.codex/skills/brainstorming/SKILL.md
- `coctostan/pi-superpowers-plus/skills/brainstorming/SKILL.md` — https://github.com/coctostan/pi-superpowers-plus/blob/main/skills/brainstorming/SKILL.md
- `mengsi16/plan-for-all/skills/brainstorming/SKILL.md` — https://github.com/mengsi16/plan-for-all/blob/main/skills/brainstorming/SKILL.md

### 3. Add questioning-or-interaction protocol

Observed across 7 mutation groups in 7 repositories.

**What changed.** Concrete questioning behavior (one question at a time, tool usage, question counts).

**Why it may matter.** (interpretation) Unstructured questioning degenerates into interrogation or guesswork.

**Tradeoff.** (interpretation) Tradeoff: protocol can feel mechanical.

Representative implementations:

- `JsonLee12138/prompts/skills/brainstorming/SKILL.md` — https://github.com/JsonLee12138/prompts/blob/main/skills/brainstorming/SKILL.md
- `letitbk/claude-academic-setup/skills/brainstorming/SKILL.md` — https://github.com/letitbk/claude-academic-setup/blob/main/skills/brainstorming/SKILL.md
- `casius-connect/vibe-briefing-skills/skills/brainstorming/SKILL.md` — https://github.com/casius-connect/vibe-briefing-skills/blob/main/skills/brainstorming/SKILL.md

### 4. Add diverge/converge phase split

Observed across 4 mutation groups in 4 repositories.

**What changed.** Explicit divergent exploration followed by convergent presentation.

**Why it may matter.** (interpretation) Prevents premature commitment to the first idea.

**Tradeoff.** (interpretation) Tradeoff: longer process for small decisions.

Representative implementations:

- `aAAaqwq/AGI-Super-Team/skills/sp-brainstorming/SKILL.md` — https://github.com/aAAaqwq/AGI-Super-Team/blob/main/skills/sp-brainstorming/SKILL.md
- `himmelreich-it/agent-skill-converter/out/junie/skills/superpowers/skills/brainstorming/SKILL.md` — https://github.com/himmelreich-it/agent-skill-converter/blob/main/out/junie/skills/superpowers/skills/brainstorming/SKILL.md
- `myths-labs/muse/skills/toolkit/brainstorming/SKILL.md` — https://github.com/myths-labs/muse/blob/main/skills/toolkit/brainstorming/SKILL.md

### 5. Add greenfield-vs-existing path split

Observed across 3 mutation groups in 3 repositories.

**What changed.** Distinct paths for new projects versus established codebases.

**Why it may matter.** (interpretation) Context exploration differs fundamentally between the two.

**Tradeoff.** (interpretation) Tradeoff: more branches to maintain.

Representative implementations:

- `derHaken/SuperAntigravity/skills/brainstorming/SKILL.md` — https://github.com/derHaken/SuperAntigravity/blob/main/skills/brainstorming/SKILL.md
- `kyaulabs/prism/packages/prism-core/skills/brainstorming/SKILL.md` — https://github.com/kyaulabs/prism/blob/main/packages/prism-core/skills/brainstorming/SKILL.md
- `Benkapner/claude-code-basecamp/skills/brainstorming/SKILL.md` — https://github.com/Benkapner/claude-code-basecamp/blob/main/skills/brainstorming/SKILL.md

## Notable one-off adaptations

Several groups implement unique changes that do not recur across families; the full group list with per-group source links is in the evidence payload (`*-evidence.json`).

## Caveats

- GitHub code search is not a complete census; counts are a floor.
- Recurrence is not quality; motifs are observations, not recommendations.
- No ancestry is claimed; identical hashes prove identical bytes only.
- Archetypes and motifs are heuristic descriptive categories, not a formal taxonomy.
