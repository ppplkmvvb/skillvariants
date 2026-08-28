# Add Red Flags And Anti Pattern Guard

Observed across:
- 4 distinct mutation groups
- 4 repositories
- 6 total occurrences

## What changed
Structural/behavioral delta extracted from supporting group records:
- length_delta: +89%, -54%, -32% ...
- headings net added: 70 vs removed: 45
- semantic-consistency (first-label): 2/4 = 50%

Why it may matter: making violation of the workflow a named, stoppable condition lets a recursive agent catch itself mid-mistake.

## Representative implementations

### MadAppGang/claude-code/plugins/dev/skills/discipline/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/MadAppGang/claude-code/blob/main/plugins/dev/skills/discipline/systematic-debugging/SKILL.md
Added evidence: ++ | **Iron Law:** "NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST" | Use this skill when:
Removed evidence: -- | ## Overview | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.
Manual worth_reviewing: YES

### aiskillstore/marketplace/skills/codingcossack/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/aiskillstore/marketplace/blob/main/skills/codingcossack/systematic-debugging/SKILL.md
Added evidence: ++ | **Core principle:** Find root cause before attempting fixes. Symptom fixes are failure. | ## Phase 1: Root Cause Investigation
Removed evidence: -- | ## Overview | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.
Manual worth_reviewing: YES

### VidyaBodepudi/Code-Skills/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/VidyaBodepudi/Code-Skills/blob/main/skills/systematic-debugging/SKILL.md
Added evidence: ++ | Systematic debugging prevents the #1 agent anti-pattern: guessing at fixes. Instead of trying random changes and hoping something works
Removed evidence: -- | # Systematic Debugging | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

### byerlikaya/claude-starter-kit/plugin/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/byerlikaya/claude-starter-kit/blob/main/plugin/skills/systematic-debugging/SKILL.md
Added evidence: ++ | <!-- routing-eval reads this line; it lives in the BODY so the always-on skill LISTING stays inside | Claude Code's budget (1% of the c
Removed evidence: -- | ## Overview | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.
Manual worth_reviewing: YES

## Counterexamples / ambiguity
- 2 supporting groups carry this motif only as a secondary label.
- Some members are plausibly derived from the original superpowers file rather than independently authored (see depth report §8).

Confidence: MEDIUM (4 groups but wording is heterogeneous; 2/4 share the exact Red Flags heading).
