# Using SkillVariants from your agent

SkillVariants Core finds and structures the evidence. The Skill lets your
agent interpret it.

The repository ships an installable Agent Skill (`skills/skillvariants/`)
that teaches a coding agent to run the deterministic pipeline and then
perform semantic motif analysis on top of it — with strict guardrails
against fabrication, ancestry claims, and frequency-as-quality reasoning.

## Install

Copy or symlink `skills/skillvariants/` into your agent's skills directory
(for example `.claude/skills/skillvariants/`, `.agents/skills/skillvariants/`,
or the equivalent for your tool), or point your agent at the folder directly.

Requirements for the agent's environment:

- Python 3.11+
- `uvx skillvariants` (or `pipx install skillvariants`) on PATH
- GitHub authentication: `GITHUB_TOKEN` or `gh auth login`

## Example prompt

```text
Study how this Skill has been adapted across GitHub:
https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md
Identify recurring concrete adaptations, show supporting implementations,
and distinguish evidence from interpretation.
```

The agent will run `skillvariants evidence <url> --json`, analyze the
mutation groups, consolidate motifs under strict invariants, verify
recurrence counts deterministically, and present an evidence-backed study.
A real output of this workflow is preserved in
`research/agent-benchmark/v1/runs/systematic-debugging-study.md` and
summarized in `skills/skillvariants/examples/systematic-debugging.md`.

## Direct CLI alternative

If you do not want an Agent Skill, everything is available from the terminal:

```bash
skillvariants related <url>                  # archetype map
skillvariants evidence <url> --json          # machine-readable evidence
skillvariants compare <url-a> <url-b> --json # structural diff of two skills
```

## Validation status

The agent semantic layer was benchmarked against a frozen 243-group human
baseline across three skill families
([report](research/agent-benchmark/v1/agent-semantic-report.md)):
meaningful-change agreement 100% (upper bound — same model authored the
baseline), 86% of strong human motifs recovered, 0 fabricated sources, but
26% of recurring agent motifs required splitting for over-merge. Consequence:
the skill presents agent-consolidated motifs as **proposals validated by
deterministic invariant checks**, and recurrence is always computed by
SkillVariants code, never by the model.
