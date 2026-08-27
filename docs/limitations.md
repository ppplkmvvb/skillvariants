# Limitations

Be skeptical of any single result. This list is the honest contract of v0.1.

## Search coverage

- GitHub Code Search is **not a complete census**: indexing skips some forks,
  newly-pushed repos, and non-default branches. Result counts change over time
  as GitHub re-indexes.
- Candidate discovery is same-name based (`"name: <x>" filename:SKILL.md`).
  A fork that renamed the skill is invisible to discovery in v0.1.
- Pagination caps at ~1000 search results per query per run.

## Classification & scoring

- **Archetypes overlap by design** — especially `workflow-specialization` vs
  `project-specialization`. One deterministic primary label is chosen; treat
  it as a strong hint, not ground truth. (Backlog item #1 refines this.)
- Relatedness is heuristic (token overlap + heading Jaccard + description
  similarity). Same-name collisions with unrelated content are capped below
  the gate but not eliminated.
- Placeholder/template skeletons are penalized in representative ranking but
  still occupy slots when few better candidates exist in an archetype.
- Absorber resistance uses raw-text coherence; a well-edited absorber could
  evade it.
- All thresholds were calibrated on three high-copy families (see
  `research/validation-summary.md`). Behavior on sparse families (few or zero
  variants) is unvalidated beyond smoke tests.

## Semantics

- **No ancestry proof** — never read output as "original", "copied from", or
  "forked from". Hash identity proves identical bytes, nothing more.
- Results describe repositories at fetch time; upstream edits change future
  runs (determinism holds only per cached candidate set).
- Private repositories are outside default public code-search behavior.

## Not security tooling

SkillVariants reports structure and text deltas. It does not audit, sandbox,
or rate the safety of any Skill, command, URL, or author, and must not be used
as a trust signal.

## Deferred (v0.1 backlog)

1. taxonomy refinement (workflow vs project)
2. larger blind validation set
3. GitSkills/offline index exploration
4. historical / earliest-observed metadata
5. shareable static reports
6. optional semantic explanation
7. web explorer only if the CLI gets traction
8. stronger placeholder detection if users report cases
