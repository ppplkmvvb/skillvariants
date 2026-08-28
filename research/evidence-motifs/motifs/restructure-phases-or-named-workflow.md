# Restructure Phases Or Named Workflow

Observed across:
- 9 distinct mutation groups
- 8 repositories
- 10 total occurrences

## What changed
Structural/behavioral delta extracted from supporting group records:
- length_delta: -80%, -41%, -73% ...
- headings net added: 69 vs removed: 102
- semantic-consistency (first-label): 9/9 = 100%

Why it may matter: most teams adapt the four phases to their own pipeline (Fagan inspection, feedback-loop-first, repro->isolate->identify->fix), proving the taxonomy is genuinely re-authorized rather than copied.

## Representative implementations

### skeletorflet/opencode-supreme-setup/.claude/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/skeletorflet/opencode-supreme-setup/blob/master/.claude/skills/systematic-debugging/SKILL.md
Added evidence: ++ | Random fixes waste time and create new bugs. Quick patches mask underlying issues. | 1. Read Error Messages Carefully - don't skip past
Removed evidence: -- | **Violating the letter of this process is violating the spirit of debugging.** | ```

### aiskillstore/marketplace/skills/asmayaseen/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/aiskillstore/marketplace/blob/main/skills/asmayaseen/systematic-debugging/SKILL.md
Added evidence: ++ | Random fixes waste time and create new bugs. Quick patches mask underlying issues. | ---
Removed evidence: -- | ## Overview | **Violating the letter of this process is violating the spirit of debugging.**

### David-Li0406/meta-skill-evloving/skill-flow/data/skills-refined-36k/skillsmp/systematic-debugging-15/SKILL.md
Direct SKILL.md URL: https://github.com/David-Li0406/meta-skill-evloving/blob/main/skill-flow/data/skills-refined-36k/skillsmp/systematic-debugging-15/SKILL.md
Added evidence: ++ | Random fixes waste time and create new bugs. Quick patches mask underlying issues. | **Use ESPECIALLY when:**
Removed evidence: -- | ## Overview | **Violating the letter of this process is violating the spirit of debugging.**

### RBraga01/a-team/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/RBraga01/a-team/blob/main/skills/systematic-debugging/SKILL.md
Added evidence: ++ | Quick patches mask underlying issues. Systematic debugging is FASTER than thrashing. | ## The Four Phases (Must Complete in Order)
Removed evidence: -- | ## Overview | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.
Manual worth_reviewing: YES

### tmdgusya/engineering-discipline/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/tmdgusya/engineering-discipline/blob/main/skills/systematic-debugging/SKILL.md
Added evidence: ++ | A strict debugging workflow. Use when dealing with bugs, test failures, or unexpected behavior. | Three core purposes:
Removed evidence: -- | ## Overview | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.
Manual worth_reviewing: YES

### CUBETIQ/cubis-foundry/workflows/workflows/agent-environment-setup/platforms/claude/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/CUBETIQ/cubis-foundry/blob/main/workflows/workflows/agent-environment-setup/platforms/claude/skills/systematic-debugging/SKILL.md
Added evidence: ++ | # Systematic Debugging Methodology | ## Purpose
Removed evidence: -- | # Systematic Debugging | ## Overview

### ArchieIndian/openclaw-superpowers/skills/core/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/ArchieIndian/openclaw-superpowers/blob/main/skills/core/systematic-debugging/SKILL.md
Added evidence: ++ | Never guess at fixes. Find the root cause first. | ## Phase 1: Understand the Error
Removed evidence: -- | ## Overview | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

### sammcj/agentic-coding/Skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/sammcj/agentic-coding/blob/main/Skills/systematic-debugging/SKILL.md
Added evidence: ++ | # Systematic Debugging with Fagan Inspection | This skill applies a modified Fagan Inspection methodology for systematic problem resolu
Removed evidence: -- | # Systematic Debugging | ## Overview

### David-Li0406/meta-skill-evloving/skill-flow/data/skills-refined-36k/skillsmp/systematic-debugging-53/SKILL.md
Direct SKILL.md URL: https://github.com/David-Li0406/meta-skill-evloving/blob/main/skill-flow/data/skills-refined-36k/skillsmp/systematic-debugging-53/SKILL.md
Added evidence: ++ | ## What I Do | - Guide systematic root cause analysis
Removed evidence: -- | # Systematic Debugging | ## Overview

## Counterexamples / ambiguity
- 0 supporting groups carry this motif only as a secondary label.
- Some members are plausibly derived from the original superpowers file rather than independently authored (see depth report §8).

Confidence: MEDIUM (9 groups but 4 are worth=MAYBE; mostly maintainer-adjacent).
