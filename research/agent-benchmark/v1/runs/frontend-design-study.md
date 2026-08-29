# SkillVariants study — frontend-design

Target: [anthropics/skills/skills/frontend-design/SKILL.md](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md) (ref `main`)

## Corpus summary (deterministic)

- Candidate matches: 300
- Unique related variants: 189
- Exact copies collapsed: 12
- Mutation groups: 68
- Broad archetypes: workflow-specialization 33, compact-rewrite 14, routing-specialization 9, no-label 6, expanded-guidance 4, body-copy-with-metadata-change 1, compatibility-wrapper 1

## Recurring adaptations

### 1. Add framework-specific design rules

Observed across 5 mutation groups in 5 repositories.

**What changed.** Rules tied to a concrete UI stack (shadcn/ui, React/Next.js, Tailwind tokens, stack priority).

**Why it may matter.** (interpretation) Generic aesthetic guidance may not survive contact with a real component library.

**Tradeoff.** (interpretation) Tradeoff: couples the skill to a stack version.

Representative implementations:

- `studio-jami/jami-studio/templates/forms/.agents/skills/frontend-design/SKILL.md` — https://github.com/studio-jami/jami-studio/blob/main/templates/forms/.agents/skills/frontend-design/SKILL.md
- `Everfern-AI/Everfern/main/skills/frontend-design/SKILL.md` — https://github.com/Everfern-AI/Everfern/blob/main/main/skills/frontend-design/SKILL.md
- `roerohan/skills/frontend-design/SKILL.md` — https://github.com/roerohan/skills/blob/main/frontend-design/SKILL.md

### 2. Add evaluation-or-review gate

Observed across 5 mutation groups in 5 repositories.

**What changed.** An explicit review/verification gate output must pass before delivery.

**Why it may matter.** (interpretation) Generated UI is rarely reviewed against intent without a forced pass.

**Tradeoff.** (interpretation) Tradeoff: checklists can become boilerplate.

Representative implementations:

- `rongxinzy/RongxinAI/SKILLs/frontend-design/SKILL.md` — https://github.com/rongxinzy/RongxinAI/blob/main/SKILLs/frontend-design/SKILL.md
- `mohitagw15856/pm-claude-skills/skills/frontend-design/SKILL.md` — https://github.com/mohitagw15856/pm-claude-skills/blob/main/skills/frontend-design/SKILL.md
- `byerlikaya/claude-starter-kit/plugin/skills/frontend-design/SKILL.md` — https://github.com/byerlikaya/claude-starter-kit/blob/main/plugin/skills/frontend-design/SKILL.md

### 3. Add contract/scope/output gates

Observed across 4 mutation groups in 4 repositories.

**What changed.** Defines when the skill applies and what it must produce (triggers, output contracts, DESIGN.md).

**Why it may matter.** (interpretation) Prevents drift into generic implementation work.

**Tradeoff.** (interpretation) Tradeoff: upfront friction.

Representative implementations:

- `archibate/dotfiles-opencode/skills/frontend-design/SKILL.md` — https://github.com/archibate/dotfiles-opencode/blob/main/skills/frontend-design/SKILL.md
- `samilozturk/agentlint/skills/frontend/SKILL.md` — https://github.com/samilozturk/agentlint/blob/main/skills/frontend/SKILL.md
- `ceilf6/FrontAgent/skills/frontend-design/SKILL.md` — https://github.com/ceilf6/FrontAgent/blob/develop/skills/frontend-design/SKILL.md

### 4. Add project-specific rules

Observed across 3 mutation groups in 3 repositories.

**What changed.** Rules grounded in this repo's design language, context files, or platform quirks.

**Why it may matter.** (interpretation) Adapts a generic skill into a project design system.

**Tradeoff.** (interpretation) Tradeoff: not reusable outside the project.

Representative implementations:

- `quocthinhthan/Portfolio/.agents/skills/frontend-design/SKILL.md` — https://github.com/quocthinhthan/Portfolio/blob/main/.agents/skills/frontend-design/SKILL.md
- `tschuehly/lexware/.agents/skills/frontend-design/SKILL.md` — https://github.com/tschuehly/lexware/blob/main/.agents/skills/frontend-design/SKILL.md
- `pavanchanduri/expense-tracker/.claude/skills/frontend-design/SKILL.md` — https://github.com/pavanchanduri/expense-tracker/blob/master/.claude/skills/frontend-design/SKILL.md

## Notable one-off adaptations

Several groups implement unique changes that do not recur across families; the full group list with per-group source links is in the evidence payload (`*-evidence.json`).

## Caveats

- GitHub code search is not a complete census; counts are a floor.
- Recurrence is not quality; motifs are observations, not recommendations.
- No ancestry is claimed; identical hashes prove identical bytes only.
- Archetypes and motifs are heuristic descriptive categories, not a formal taxonomy.
