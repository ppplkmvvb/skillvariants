# Preserve Root Cause First While Compressing

Observed across:
- 5 distinct mutation groups
- 5 repositories
- 6 total occurrences

## What changed
Structural/behavioral delta extracted from supporting group records:
- length_delta: -16%, -60%, -91% ...
- headings net added: 31 vs removed: 58
- semantic-consistency (first-label): 5/5 = 100%

Why it may matter: a real tradeoff — teams choose brevity over completeness while keeping the single governing invariant; the 'compressed but not broken' adaptation is the strongest evidence of deliberate authoring.

## Representative implementations

### PytaichukBohdan/AndriiPresentation/.claude/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/PytaichukBohdan/AndriiPresentation/blob/main/.claude/skills/systematic-debugging/SKILL.md
Added evidence: ++ | Debug systematically. Understand before fixing. One change at a time. | **Core principle:** A bug fixed without understanding is a bug 
Removed evidence: -- | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure. | **Violating the letter of this process
Manual worth_reviewing: YES

### majiayu000/spellbook/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/majiayu000/spellbook/blob/main/skills/systematic-debugging/SKILL.md
Added evidence: ++ | > From [obra/superpowers](https://github.com/obra/superpowers) | ## Core Principle
Removed evidence: -- | ## Overview | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.
Manual worth_reviewing: YES

### GuicedEE/ai-rules/skills/.curated/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/GuicedEE/ai-rules/blob/master/skills/.curated/systematic-debugging/SKILL.md
Added evidence: ++ | Always investigate root cause before proposing fixes. | ## Core Rule
Removed evidence: -- | ## Overview | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.
Manual worth_reviewing: YES

### hnb-rabear/RCore/.agents/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/hnb-rabear/RCore/blob/main/.agents/skills/systematic-debugging/SKILL.md
Added evidence: ++ | > Adapted from [superpowers:systematic-debugging](https://github.com/obra/superpowers) | NEVER guess at fixes. Find the root cause FIRS
Removed evidence: -- | ## Overview | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

### Archive228/loopkit/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/Archive228/loopkit/blob/main/skills/systematic-debugging/SKILL.md
Added evidence: ++ | The single most expensive agent failure: seeing an error and immediately generating a | "fix" based on the error type, without reading 
Removed evidence: -- | ## Overview | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.
Manual worth_reviewing: YES

## Counterexamples / ambiguity
- 0 supporting groups carry this motif only as a secondary label.
- Some members are plausibly derived from the original superpowers file rather than independently authored (see depth report §8).

Confidence: HIGH (5/5 first-label).
