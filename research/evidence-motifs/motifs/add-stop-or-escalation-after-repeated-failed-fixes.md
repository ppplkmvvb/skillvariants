# Add Stop Or Escalation After Repeated Failed Fixes

Observed across:
- 9 distinct mutation groups
- 9 repositories
- 11 total occurrences

## What changed
Structural/behavioral delta extracted from supporting group records:
- length_delta: -54%, -75%, -75% ...
- headings net added: 71 vs removed: 108
- semantic-consistency (first-label): 8/9 = 89%

Why it may matter: after N failed hypotheses, continuing the loop is the most common actual failure mode of the debugging skill; multiple teams independently add an escape valve that preserves the workflow but bounds it.

## Representative implementations

### aiskillstore/marketplace/skills/codingcossack/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/aiskillstore/marketplace/blob/main/skills/codingcossack/systematic-debugging/SKILL.md
Added evidence: ++ | **Core principle:** Find root cause before attempting fixes. Symptom fixes are failure. | ## Phase 1: Root Cause Investigation
Removed evidence: -- | ## Overview | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.
Manual worth_reviewing: YES

### RBraga01/a-team/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/RBraga01/a-team/blob/main/skills/systematic-debugging/SKILL.md
Added evidence: ++ | Quick patches mask underlying issues. Systematic debugging is FASTER than thrashing. | ## The Four Phases (Must Complete in Order)
Removed evidence: -- | ## Overview | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.
Manual worth_reviewing: YES

### jh941213/my-cc-harness/skills_en/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/jh941213/my-cc-harness/blob/main/skills_en/systematic-debugging/SKILL.md
Added evidence: ++ | **Iron law: no fixes without root-cause investigation. Fixing symptoms is failure.** | The simpler the bug looks, the more urgent the s
Removed evidence: -- | ## Overview | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.
Manual worth_reviewing: YES

### Bbeierle12/Skill-MCP-Claude/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/Bbeierle12/Skill-MCP-Claude/blob/main/skills/systematic-debugging/SKILL.md
Added evidence: ++ | ## Core Principle | **Don't guess. Investigate systematically.**
Removed evidence: -- | ## Overview | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.
Manual worth_reviewing: YES

### majiayu000/spellbook/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/majiayu000/spellbook/blob/main/skills/systematic-debugging/SKILL.md
Added evidence: ++ | > From [obra/superpowers](https://github.com/obra/superpowers) | ## Core Principle
Removed evidence: -- | ## Overview | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.
Manual worth_reviewing: YES

### erclx/aitk/claude/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/erclx/aitk/blob/main/claude/skills/systematic-debugging/SKILL.md
Added evidence: ++ | # Systematic debugging | Random fixes waste time and create new bugs. Before proposing any fix, complete the four phases below in order
Removed evidence: -- | # Systematic Debugging | ## Overview
Manual worth_reviewing: YES

### jed72/compass/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/jed72/compass/blob/main/skills/systematic-debugging/SKILL.md
Added evidence: ++ | A test failed and you did not expect it to. The reflex is to change something | plausible and re-run. That reflex is why debugging sess
Removed evidence: -- | ## Overview | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.
Manual worth_reviewing: YES

### Archive228/loopkit/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/Archive228/loopkit/blob/main/skills/systematic-debugging/SKILL.md
Added evidence: ++ | The single most expensive agent failure: seeing an error and immediately generating a | "fix" based on the error type, without reading 
Removed evidence: -- | ## Overview | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.
Manual worth_reviewing: YES

### ericbusboom/dotconfig/.agents/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/ericbusboom/dotconfig/blob/master/.agents/skills/systematic-debugging/SKILL.md
Added evidence: ++ | # Systematic Debugging Skill | A structured debugging protocol that replaces ad hoc fix attempts.
Removed evidence: -- | # Systematic Debugging | ## Overview
Manual worth_reviewing: YES

## Counterexamples / ambiguity
- 1 supporting groups carry this motif only as a secondary label.
- Some members are plausibly derived from the original superpowers file rather than independently authored (see depth report §8).

Confidence: HIGH (9 groups, 9 repos, all worth=YES).
