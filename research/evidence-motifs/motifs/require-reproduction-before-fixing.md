# Require Reproduction Before Fixing

Observed across:
- 5 distinct mutation groups
- 5 repositories
- 21 total occurrences

## What changed
Structural/behavioral delta extracted from supporting group records:
- length_delta: -77%, -91%, -93% ...
- headings net added: 47 vs removed: 69
- semantic-consistency (first-label): 5/5 = 100%

Why it may matter: 'never fix what you cannot reproduce' is the canonical first phase of every debugging methodology; localizing it as a hard rule is a shared adaptation.

## Representative implementations

### pratikrath126/ai-image-detector/.agent/kit-skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/pratikrath126/ai-image-detector/blob/main/.agent/kit-skills/systematic-debugging/SKILL.md
Added evidence: ++ | > Source: obra/superpowers | This skill provides a structured approach to debugging that prevents random guessing and ensures problems 
Removed evidence: -- | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure. | **Violating the letter of this process

### yimwoo/hotl-plugin/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/yimwoo/hotl-plugin/blob/main/skills/systematic-debugging/SKILL.md
Added evidence: ++ | ## Four Phases | ### Phase 1: Reproduce
Removed evidence: -- | ## Overview | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

### RakuenSoftware/aimee/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/RakuenSoftware/aimee/blob/testing/skills/systematic-debugging/SKILL.md
Added evidence: ++ | Start with evidence, not guesses. | 1. Reproduce the failure with the smallest command, input, or trace available.
Removed evidence: -- | ## Overview | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

### DDS-Solutions/AI-TadPole-OS/.agent/skills/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/DDS-Solutions/AI-TadPole-OS/blob/main/.agent/skills/systematic-debugging/SKILL.md
Added evidence: ++ | > [!IMPORTANT] | > **AI Context & Knowledge Heritage**
Removed evidence: -- | **Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure. | **Violating the letter of this process

### New1Direction/korgex/src/skills_builtin/systematic-debugging/SKILL.md
Direct SKILL.md URL: https://github.com/New1Direction/korgex/blob/main/src/skills_builtin/systematic-debugging/SKILL.md
Added evidence: ++ | Resist the urge to guess-and-patch. A bug you can't reproduce isn't fixed. | 1. **Reproduce reliably.** Find the smallest, deterministi
Removed evidence: -- | # Systematic Debugging | ## Overview

## Counterexamples / ambiguity
- 0 supporting groups carry this motif only as a secondary label.
- Some members are plausibly derived from the original superpowers file rather than independently authored (see depth report §8).

Confidence: HIGH (5/5 first-label, 5 repos).
