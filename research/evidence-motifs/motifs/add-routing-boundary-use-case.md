# Add Routing Boundary Use Case

Observed across:
- 4 distinct mutation groups
- 4 repositories
- 4 total occurrences

## What changed
Structural/behavioral delta extracted from supporting group records:
- length_delta: -67%, +42%, -46% ...
- headings net added: 35 vs removed: 41
- semantic-consistency (first-label): 4/4 = 100%

Why it may matter: a debugging skill that fires on 'whenever' causes over-application; explicit use/do-not-use boundaries are a cheap containment strategy. Note: 3 of these are also 'use-case boundary' variants (Emergency Stop, Refuse Gate) rather than true routing.

## Representative implementations

### itseffi/agentic-os/.agents/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/itseffi/agentic-os/blob/main/.agents/skills/systematic-debugging/SKILL.md
Added evidence: ++ | Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes. | - If not reproducible, gather more data
Removed evidence: -- | ## Overview | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.
Manual worth_reviewing: YES

### FradSer/dotclaude/superpowers/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/FradSer/dotclaude/blob/main/superpowers/skills/systematic-debugging/SKILL.md
Added evidence: ++ | ## Slash-command Usage | Invoked via `/superpowers:systematic-debugging "<symptom>"` or auto-loaded by other skills when bug-fix langua
Removed evidence: -- | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure. | **Violating the letter of this process
Manual worth_reviewing: YES

### SethGammon/Citadel/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/SethGammon/Citadel/blob/main/skills/systematic-debugging/SKILL.md
Added evidence: ++ | # /systematic-debugging — Root Cause Before Fix | ## Orientation
Removed evidence: -- | # Systematic Debugging | ## Overview
Manual worth_reviewing: YES

### baphuongna/pi-crew/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/baphuongna/pi-crew/blob/main/skills/systematic-debugging/SKILL.md
Added evidence: ++ | # systematic-debugging | Core principle: no fixes without root-cause investigation first. Symptom patches create new bugs and hide the 
Removed evidence: -- | # Systematic Debugging | ## Overview

## Counterexamples / ambiguity
- 0 supporting groups carry this motif only as a secondary label.
- Some members are plausibly derived from the original superpowers file rather than independently authored (see depth report §8).

Confidence: MEDIUM (4 groups; cluster share 50% at threshold).
