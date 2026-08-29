# SkillVariants study — systematic-debugging

## Target Skill

[https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md](https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md)

## Corpus summary

Mutation groups: 85; analyzed: 85; exact copies collapsed: 0.

## Recurring adaptations

1. add stop or escalation after repeated failed fixes
   Observed across 8 groups in 8 repositories.
   Invariant: Introduces an explicit termination, escalation, or reframing trigger tied to a counted number of failed fix attempts.
   (interpretation) Why it may matter is documented in the family study.
   - aiskillstore/marketplace/skills/codingcossack/systematic-debugging/SKILL.md — https://github.com/aiskillstore/marketplace/blob/main/skills/codingcossack/systematic-debugging/SKILL.md
   - RBraga01/a-team/skills/systematic-debugging/SKILL.md — https://github.com/RBraga01/a-team/blob/main/skills/systematic-debugging/SKILL.md
   - jh941213/my-cc-harness/skills_en/systematic-debugging/SKILL.md — https://github.com/jh941213/my-cc-harness/blob/main/skills_en/systematic-debugging/SKILL.md
2. add project or product specific design rules
   Observed across 6 groups in 6 repositories.
   Invariant: Adds design or debugging rules grounded in this specific repository, product, or its design language.
   (interpretation) Why it may matter is documented in the family study.
   - eastreams/loong/skills/systematic-debugging/SKILL.md — https://github.com/eastreams/loong/blob/rewrite/skills/systematic-debugging/SKILL.md
   - LiGoldragon/Mentci-AI/.pi/skills/systematic-debugging/SKILL.md — https://github.com/LiGoldragon/Mentci-AI/blob/main/.pi/skills/systematic-debugging/SKILL.md
   - Frostthejack/hermes-tailscale-rw/profiles/orchestrator/skills/software-development/systematic-debugging/SKILL.md — https://github.com/Frostthejack/hermes-tailscale-rw/blob/main/profiles/orchestrator/skills/software-development/systematic-debugging/SKILL.md
3. route completion verification to separate skill
   Observed across 5 groups in 5 repositories.
   Invariant: Delegates final completion/verification checking to another named skill or a separate verification step.
   (interpretation) Why it may matter is documented in the family study.
   - coctostan/pi-superpowers-plus/skills/systematic-debugging/SKILL.md — https://github.com/coctostan/pi-superpowers-plus/blob/main/skills/systematic-debugging/SKILL.md
   - coco-research/coco/skills/systematic-debugging/SKILL.md — https://github.com/coco-research/coco/blob/main/skills/systematic-debugging/SKILL.md
   - bg-szy/TOP-SKILLS/skills/agent-skills/systematic-debugging/SKILL.md — https://github.com/bg-szy/TOP-SKILLS/blob/master/skills/agent-skills/systematic-debugging/SKILL.md
4. require reproduction before fixing
   Observed across 4 groups in 4 repositories.
   Invariant: Makes producing a reproduction (or explicit handling of non-reproducibility) a required, gated step before any fix.
   (interpretation) Why it may matter is documented in the family study.
   - yimwoo/hotl-plugin/skills/systematic-debugging/SKILL.md — https://github.com/yimwoo/hotl-plugin/blob/main/skills/systematic-debugging/SKILL.md
   - DDS-Solutions/AI-TadPole-OS/.agent/skills/systematic-debugging/SKILL.md — https://github.com/DDS-Solutions/AI-TadPole-OS/blob/main/.agent/skills/systematic-debugging/SKILL.md
   - New1Direction/korgex/src/skills_builtin/systematic-debugging/SKILL.md — https://github.com/New1Direction/korgex/blob/main/src/skills_builtin/systematic-debugging/SKILL.md
5. add feedback loop rule
   Observed across 3 groups in 3 repositories.
   Invariant: Elevates building/validating a feedback loop (reproduction plus instrumentation) into a named, mandatory rule.
   (interpretation) Why it may matter is documented in the family study.
   - 7757/Fan-Browser-Agent/skills/software-development/systematic-debugging/SKILL.md — https://github.com/7757/Fan-Browser-Agent/blob/main/skills/software-development/systematic-debugging/SKILL.md
   - MezbahSaif/HermesBench/Case1_Qwen/datasets/variants/tasks/skills/software-development/systematic-debugging/SKILL.md — https://github.com/MezbahSaif/HermesBench/blob/main/Case1_Qwen/datasets/variants/tasks/skills/software-development/systematic-debugging/SKILL.md
   - tranhieutt/software_development_department/.claude/skills/systematic-debugging/SKILL.md — https://github.com/tranhieutt/software_development_department/blob/main/.claude/skills/systematic-debugging/SKILL.md
6. add red flags and anti pattern guard
   Observed across 4 groups in 4 repositories.
   Invariant: Adds an explicit list of violation indicators or anti-patterns that signal the process itself is being violated.
   (interpretation) Why it may matter is documented in the family study.
   - MadAppGang/claude-code/plugins/dev/skills/discipline/systematic-debugging/SKILL.md — https://github.com/MadAppGang/claude-code/blob/main/plugins/dev/skills/discipline/systematic-debugging/SKILL.md
   - aiskillstore/marketplace/skills/codingcossack/systematic-debugging/SKILL.md — https://github.com/aiskillstore/marketplace/blob/main/skills/codingcossack/systematic-debugging/SKILL.md
   - VidyaBodepudi/Code-Skills/skills/systematic-debugging/SKILL.md — https://github.com/VidyaBodepudi/Code-Skills/blob/main/skills/systematic-debugging/SKILL.md
7. preserve root cause first while compressing
   Observed across 5 groups in 5 repositories.
   Invariant: Substantially shortens the document while explicitly retaining the root-cause-first governing rule.
   (interpretation) Why it may matter is documented in the family study.
   - GuicedEE/ai-rules/skills/.curated/systematic-debugging/SKILL.md — https://github.com/GuicedEE/ai-rules/blob/master/skills/.curated/systematic-debugging/SKILL.md
   - PytaichukBohdan/AndriiPresentation/.claude/skills/systematic-debugging/SKILL.md — https://github.com/PytaichukBohdan/AndriiPresentation/blob/main/.claude/skills/systematic-debugging/SKILL.md
   - hnb-rabear/RCore/.agents/skills/systematic-debugging/SKILL.md — https://github.com/hnb-rabear/RCore/blob/main/.agents/skills/systematic-debugging/SKILL.md
8. replace with named methodology
   Observed across 4 groups in 4 repositories.
   Invariant: Replaces the four-phase method with a different named methodology or scientific framing.
   (interpretation) Why it may matter is documented in the family study.
   - sammcj/agentic-coding/Skills/systematic-debugging/SKILL.md — https://github.com/sammcj/agentic-coding/blob/main/Skills/systematic-debugging/SKILL.md
   - CUBETIQ/cubis-foundry/workflows/workflows/agent-environment-setup/platforms/claude/skills/systematic-debugging/SKILL.md — https://github.com/CUBETIQ/cubis-foundry/blob/main/workflows/workflows/agent-environment-setup/platforms/claude/skills/systematic-debugging/SKILL.md
   - MadAppGang/claude-code/plugins/dev/skills/discipline/systematic-debugging/SKILL.md — https://github.com/MadAppGang/claude-code/blob/main/plugins/dev/skills/discipline/systematic-debugging/SKILL.md

## Notable one-offs

Suppressed/unresolved motifs: add-routing-boundary-use-case.

## Caveats

- Code search is not a census; counts are a floor.
- Recurrence is not quality; no ancestry is claimed.
- Motifs are heuristic observations, not recommendations.
