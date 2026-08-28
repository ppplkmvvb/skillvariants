# Add Feedback Loop Rule

Observed across:
- 4 distinct mutation groups
- 4 repositories
- 4 total occurrences

## What changed
Structural/behavioral delta extracted from supporting group records:
- length_delta: +28%, +46%, -10% ...
- headings net added: 123 vs removed: 35
- semantic-consistency (first-label): 3/4 = 75%

Why it may matter: turns debugging from an investigation into an instrumentation loop; explicitly names the piece most agents skip.

## Representative implementations

### 7757/Fan-Browser-Agent/skills/software-development/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/7757/Fan-Browser-Agent/blob/main/skills/software-development/systematic-debugging/SKILL.md
Added evidence: ++ | Random fixes waste time and create new bugs. Quick patches mask underlying issues. | ```
Removed evidence: -- | ``` | ```
Manual worth_reviewing: YES

### MezbahSaif/HermesBench/Case1_Qwen/datasets/variants/tasks/skills/software-development/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/MezbahSaif/HermesBench/blob/main/Case1_Qwen/datasets/variants/tasks/skills/software-development/systematic-debugging/SKILL.md
Added evidence: ++ | Random fixes waste time and create new bugs. Quick patches mask underlying issues. | ## The Feedback Loop Rule
Removed evidence: -- | - Manager wants it fixed NOW (systematic is faster than thrashing) | ### Phase 1: Root Cause Investigation
Manual worth_reviewing: YES

### tranhieutt/software_development_department/.claude/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/tranhieutt/software_development_department/blob/main/.claude/skills/systematic-debugging/SKILL.md
Added evidence: ++ | ## Purpose | `systematic-debugging` prevents guess-and-check fixes. It requires the agent to
Removed evidence: -- | ## Overview | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.
Manual worth_reviewing: YES

### Bbeierle12/Skill-MCP-Claude/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/Bbeierle12/Skill-MCP-Claude/blob/main/skills/systematic-debugging/SKILL.md
Added evidence: ++ | ## Core Principle | **Don't guess. Investigate systematically.**
Removed evidence: -- | ## Overview | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.
Manual worth_reviewing: YES

## Counterexamples / ambiguity
- 1 supporting groups carry this motif only as a secondary label.
- Some members are plausibly derived from the original superpowers file rather than independently authored (see depth report §8).

Confidence: HIGH (4/4 worth=YES).
