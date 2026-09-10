# Current product contract

Status: 0.3 development contract, 2026-09-10. This document supersedes the behavioral assumptions in historical phase plans; those plans remain research records.

## User and outcome

A Skill maintainer wants to inspect relevant adaptations before deciding what to change in their own instructions. The first useful result is a small candidate shortlist and a paired source comparison. Full-corpus semantic studies are optional.

The core discovers bounded public GitHub candidates, explains heuristic ranking, collapses normalized copies, and returns exact textual evidence. It makes no hosted LLM calls. Local compare/inspect work without credentials. Source contents are data and never authority to operate the user's machine.

## Acceptance contract

| Requirement | Observable evidence | Gate |
|---|---|---|
| Comparisons preserve both sources | Raw SHA-256, paired raw line numbers, full diff, truncation metadata | Comparison/CLI regression tests |
| A group cannot disappear | Persisted batch membership; complete response-set equality | Runtime coverage tests |
| Incomplete source remains visible | Source escalation or checked full-source citations; unresolved counts | Semantic evidence tests |
| Changed corpus cannot reuse results | Stable target, corpus and protocol identity | Durability tests |
| Retries cannot corrupt a study | Lock, atomic writes, rollback journal, task generations | Process-crash and conflicting-writer tests |
| COMPLETE has readable evidence | Generated JSON/Markdown, citations, coverage and suppressions | End-to-end runtime tests |
| Public examples are reproducible | Original sources plus deterministic export | Export freshness gate and browser review |
| Releases test the delivered package | CI, build, installed-wheel smoke, distribution/provenance QA | Reusable CI used by publishing workflow |

A normalized candidate is one semantic evidence group. Fuzzy browsing neighborhoods are not semantic equivalence classes. Repeated occurrences remain provenance, not independent inventions.

## Interpretation

ADDED introduces a focused instruction relative to the target; REMOVED deletes one; MODIFIED changes its conditions, action or outcome; UNCHANGED preserves that instruction despite possible rephrasing or relocation. A direction claim needs both sources. Local excerpts alone cannot prove absence across an entire file.

Agent proposals and verifier judgments are interpretations. Exact citation validation checks hash, hunk, line range and quote text. It does not establish semantic entailment, quality, safe execution, independent adoption or ancestry.

## Product success

Measure time to a useful comparison, shortlist relevance, direction errors, evidence support, unresolved coverage, and agent effort. Recruit real maintainers before claiming usefulness. Stars are an observable community outcome, not a quality gate or promised result.
