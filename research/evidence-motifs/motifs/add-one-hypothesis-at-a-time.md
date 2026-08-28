# Add One Hypothesis At A Time

Observed across:
- 4 distinct mutation groups
- 4 repositories
- 5 total occurrences

## What changed
Structural/behavioral delta extracted from supporting group records:
- length_delta: +89%, -96%, -94% ...
- headings net added: 66 vs removed: 54
- semantic-consistency (first-label): 4/4 = 100%

Why it may matter: the counter to shotgun debugging is to change exactly one variable and falsify it cheaply; this is the single most transferable engineering practice.

## Representative implementations

### MadAppGang/claude-code/plugins/dev/skills/discipline/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/MadAppGang/claude-code/blob/main/plugins/dev/skills/discipline/systematic-debugging/SKILL.md
Added evidence: ++ | **Iron Law:** "NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST" | Use this skill when:
Removed evidence: -- | ## Overview | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.
Manual worth_reviewing: YES

### DYAI2025/Plumbline/config/claude/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/DYAI2025/Plumbline/blob/main/config/claude/skills/systematic-debugging/SKILL.md
Added evidence: ++ | ## Loop | 1. Reproduce the failure with the smallest exact command.
Removed evidence: -- | ## Overview | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.
Manual worth_reviewing: YES

### funky-eyes/best-copilot/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/funky-eyes/best-copilot/blob/main/skills/systematic-debugging/SKILL.md
Added evidence: ++ | ## Loop | 1. Capture the exact failure and reproduction path.
Removed evidence: -- | ## Overview | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

### gabrielmoreira/agent-skills-mirror/mirrors/repos/Dokhacgiakhoa@Agent-Skills-4-Vibe-Coding-CLI/.agent/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/gabrielmoreira/agent-skills-mirror/blob/main/mirrors/repos/Dokhacgiakhoa@Agent-Skills-4-Vibe-Coding-CLI/.agent/skills/systematic-debugging/SKILL.md
Added evidence: ++ | > Source: obra/superpowers | This skill provides a structured approach to debugging that prevents random guessing and ensures problems 
Removed evidence: -- | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure. | **Violating the letter of this process

## Counterexamples / ambiguity
- 0 supporting groups carry this motif only as a secondary label.
- Some members are plausibly derived from the original superpowers file rather than independently authored (see depth report §8).

Confidence: MEDIUM (only 4 groups, wording varies, but all preserve the intent).
