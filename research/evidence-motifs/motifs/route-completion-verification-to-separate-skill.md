# Route Completion Verification To Separate Skill

Observed across:
- 5 distinct mutation groups
- 5 repositories
- 19 total occurrences

## What changed
Structural/behavioral delta extracted from supporting group records:
- length_delta: +5%, -22%, +28% ...
- headings net added: 21 vs removed: 24
- semantic-consistency (first-label): 4/5 = 80%

Why it may matter: distinguishing root-cause finding from success-claiming solves a real verification gap; several repos moved verification to a separate completion skill explicitly.

## Representative implementations

### coco-research/coco/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/coco-research/coco/blob/main/skills/systematic-debugging/SKILL.md
Added evidence: ++ | **Announce at start:** "Systematic Debugging skill activated." | Random fixes waste time and create new bugs. Quick patches mask underl
Removed evidence: -- | - Use the `superpowers:verification-before-completion` skill before claiming success | - "Ultra-think this" - Question fundamentals, no
Manual worth_reviewing: YES

### coctostan/pi-superpowers-plus/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/coctostan/pi-superpowers-plus/blob/main/skills/systematic-debugging/SKILL.md
Added evidence: ++ | > **Related skills:** Write a failing test for the bug with `/skill:test-driven-development`. Verify the fix with `/skill:verification-
Removed evidence: -- | Use for ANY technical issue: | - Test failures
Manual worth_reviewing: YES

### bg-szy/TOP-SKILLS/skills/agent-skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/bg-szy/TOP-SKILLS/blob/master/skills/agent-skills/systematic-debugging/SKILL.md
Added evidence: ++ | Random fixes waste time and create new bugs. Quick patches mask underlying issues. | See skills/root-cause-tracing for backward tracing
Removed evidence: -- | See `root-cause-tracing.md` in this directory for the complete backward tracing technique. | - Use the `superpowers:test-driven-develop
Manual worth_reviewing: YES

### apenlor/opencode-expert-mode/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/apenlor/opencode-expert-mode/blob/main/skills/systematic-debugging/SKILL.md
Added evidence: ++ | Random fixes waste time and mask underlying issues. **Core principle:** Find root cause before attempting any fix. Symptom fixes are fa
Removed evidence: -- | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure. | **Violating the letter of this process

### Threat-Vector-Security/guardian-agent/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/Threat-Vector-Security/guardian-agent/blob/main/skills/systematic-debugging/SKILL.md
Added evidence: ++ | ## Overview / When to Use | Do not guess. Find the root cause before changing code, config, or prompts. No fixes without investigation 
Removed evidence: -- | ## Overview | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.
Manual worth_reviewing: YES

## Counterexamples / ambiguity
- 1 supporting groups carry this motif only as a secondary label.
- Some members are plausibly derived from the original superpowers file rather than independently authored (see depth report §8).

Confidence: HIGH (5 groups, 5 repos, 4/5 worth=YES; one supporting group comes from the common superpowers lineage but is reworded).
