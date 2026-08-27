# Validation Summary — SkillVariants

Condensed from three internal feasibility spikes; full methodology lived in
throwaway spike repos and only conclusions ship here.

## What was validated

The premise under test across all phases:

> A developer-facing tool can automatically surface the meaningful ways an
> Agent Skill has been adapted across GitHub, without relying on an LLM.

## Three-spike evolution

| Spike | Question | Outcome |
|---|---|---|
| 1. Data spike | Can retrieval → dedupe → classify work at all? | All 5 known variants found & classified; but similarity ranking showed clone walls burying interesting mutations → REDESIGN |
| 2. Ranking redesign | Can a better global ranking surface diverse mutations? | Clone domination fixed (121 clones → 1 group); precision 90-100%; but magnitude-score bias let single archetypes fill top lists → archetype-first rethink |
| 3. Archetype-first | Is a map better than a leaderboard? | Replaced global ranking with per-archetype sections + intra-bucket scoring; all final gates passed |

The decisive lesson of spike 2/3: **"most similar" and "most interestingly
different" are different objectives**, and compressing all mutations into one
scalar list is the wrong product shape. The fix was structural (archetype map),
not another tuning round.

## Final metrics (spike 3, three families)

| Metric | Result |
|---|---:|
| Known-anchor recall | 5/5 |
| Known-anchor archetype accuracy | 5/5 |
| Displayed representative precision (correct/arguable) | 100% (34 reviewed) |
| Meaningful archetype coverage | 86% overall |
| Representative quality YES | 85% overall |
| Screenshot-story test (≥3 distinct stories/screen) | 3/3 families |
| Determinism | byte-identical JSON reruns |

## Families and anchors

- `frontend-design` — anchors: OpenBMB/PilotDeck (compact rewrite), Rain120/qq-music-api (compatibility wrapper)
- `systematic-debugging` (obra/superpowers) — anchors: Archive228/loopkit (compact rewrite), foryourhealth111-pixel/Vibe-Skills (routing specialization)
- `brainstorming` (obra/superpowers) — anchor: derHaken/SuperAntigravity (workflow specialization)

Manual labeling protocol: every displayed representative judged
correct/arguable/wrong for its section and yes/partial/no as a story, from
description, headings, signals, and excerpt — never from the tool's own score.

## Methodology constraints held throughout

- deterministic only (regex + RapidFuzz), no LLM/embeddings/vector DB
- BYO GitHub auth; filesystem cache; no telemetry
- no threshold tuned specifically to promote any anchor after the calibration pass
- anchors were regression checks, never ranking targets, once the map shipped

## Known limitations carried into v0.1

taxonomy overlap (workflow vs project), GitHub search coverage, placeholder
template edge cases, heuristic relatedness, no ancestry inference. Full list:
[docs/limitations.md](../docs/limitations.md).

## Fixtures licensing note

License-restricted upstream texts were replaced with synthetic fixtures before
release; see [fixture-audit.md](fixture-audit.md).
