# Project Specific Environment Commands

Observed across:
- 8 distinct mutation groups
- 8 repositories
- 23 total occurrences

## What changed
Structural/behavioral delta extracted from supporting group records:
- length_delta: +8%, +4%, +56% ...
- headings net added: 123 vs removed: 79
- semantic-consistency (first-label): 7/8 = 88%

Why it may matter: the adaptation that most directly turns a generic skill into an assistant for *this* repo: adding .nix rules, pipx/npx invocations, Windows/PowerShell handlers. Development ergonomics.

## Representative implementations

### eastreams/loong/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/eastreams/loong/blob/rewrite/skills/systematic-debugging/SKILL.md
Added evidence: ++ | Random fixes waste time and create new bugs. Quick patches mask underlying issues. | - Someone wants it fixed NOW (systematic is faster
Removed evidence: -- | - Manager wants it fixed NOW (systematic is faster than thrashing) | ### Phase 1: Root Cause Investigation
Manual worth_reviewing: YES

### LiGoldragon/Mentci-AI/.pi/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/LiGoldragon/Mentci-AI/blob/main/.pi/skills/systematic-debugging/SKILL.md
Added evidence: ++ | > **Related skills:** Write a failing test for the bug with `/skill:test-driven-development`. Verify the fix with `/skill:verification-
Removed evidence: -- | Use for ANY technical issue: | - Test failures
Manual worth_reviewing: YES

### Frostthejack/hermes-tailscale-rw/profiles/orchestrator/skills/software-development/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/Frostthejack/hermes-tailscale-rw/blob/main/profiles/orchestrator/skills/software-development/systematic-debugging/SKILL.md
Added evidence: ++ | Random fixes waste time and create new bugs. Quick patches mask underlying issues. | - Someone wants it fixed NOW (systematic is faster
Removed evidence: -- | - Manager wants it fixed NOW (systematic is faster than thrashing) | ### Phase 1: Root Cause Investigation

### communitiesuk/prsdb-webapp/.github/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/communitiesuk/prsdb-webapp/blob/main/.github/skills/systematic-debugging/SKILL.md
Added evidence: ++ | **Core principle:** Find root cause before attempting fixes. Symptom fixes are | failure.
Removed evidence: -- | ## Overview | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

### muyen/vibe-to-prod/.claude/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/muyen/vibe-to-prod/blob/main/.claude/skills/systematic-debugging/SKILL.md
Added evidence: ++ | # Systematic Debugging Skill | Apply structured 4-phase debugging to find root causes, not just symptoms.
Removed evidence: -- | # Systematic Debugging | ## Overview

### eng-cc/oasis7/.agents/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/eng-cc/oasis7/blob/main/.agents/skills/systematic-debugging/SKILL.md
Added evidence: ++ | Use this skill before proposing or applying a fix for: | - failing tests
Removed evidence: -- | ## Overview | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

### charlieviettq/awesome-agent-skill/.claude/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/charlieviettq/awesome-agent-skill/blob/main/.claude/skills/systematic-debugging/SKILL.md
Added evidence: ++ | # Systematic debugging | ## Iron law
Removed evidence: -- | # Systematic Debugging | ## Overview

### vamseeachanta/workspace-hub/.claude/skills/_archive/development/systematic-debugging/error-handling/SKILL.md
Direct SKILL.md URL: https://github.com/vamseeachanta/workspace-hub/blob/main/.claude/skills/_archive/development/systematic-debugging/error-handling/SKILL.md
Added evidence: ++ | # Error Handling | ## Error Handling
Removed evidence: -- | # Systematic Debugging | ## Overview

## Counterexamples / ambiguity
- 1 supporting groups carry this motif only as a secondary label.
- Some members are plausibly derived from the original superpowers file rather than independently authored (see depth report §8).

Confidence: MEDIUM (may overlap with workflow restructure; 3/8 worth=YES).
