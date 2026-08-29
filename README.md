# SkillVariants

**Let your coding agent study how Agent Skills have been adapted across GitHub.**

Deterministic GitHub evidence. Agent-powered analysis. Real implementations.

```text
hundreds of GitHub matches
   ↓  collapse copies, group near-clones
mutation groups
   ↓  behavior-equivalence clustering with a strict guardrail
recurring adaptations
   ↓  representative implementations with exact source links
```

Captured counts below are from 2026-08-29; GitHub results change over time.

## Use from your Agent

Install the bundled Agent Skill (copy `skills/skillvariants/` into your
agent's skills directory), then just ask:

```text
Study how this Skill has been adapted across GitHub:
https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md
```

The agent runs the deterministic study runtime, analyzes mutation groups,
and answers with recurring adaptations, strict counts, and real source
links — then compares any variant with the target on request. Details:
[`docs/agent-skill.md`](docs/agent-skill.md).

## Try the CLI

No SkillVariants installation is required when using [`uvx`](https://docs.astral.sh/uv/)
(the `uv` tool must be installed). GitHub Code Search authentication is
required: `GITHUB_TOKEN` or `gh auth login`.

macOS / Linux:

```bash
uvx skillvariants related \
  https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md
```

Windows PowerShell:

```powershell
uvx skillvariants related `
  https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md
```

Real output (2026-08-29 capture; full version in
[`examples/systematic-debugging.txt`](examples/systematic-debugging.txt)):

```text
SYSTEMATIC-DEBUGGING
Candidate matches found: 272

  Exact copies              0
  Unique related variants   175
  Detected mutation archetypes 4

COMPACT REWRITES
34 groups · 38 unique variants · 54 occurrences
─────────────────────────────────────────────
GuicedEE/ai-rules
  relatedness: 0.58
  length changed by -91%
  18 headings added/removed

ROUTING SPECIALIZATIONS
8 groups · 18 unique variants · 22 occurrences
─────────────────────────────────────────────
bg-szy/TOP-SKILLS
  relatedness: 0.82
  new routing-boundary language
  +6 cross-skill references
```

## Why this exists

Agent Skills get copied between repositories constantly — and the copies are
rarely identical. They get **compressed into checklists**, wrapped in thin
redirects, rerouted to sibling skills, or specialized for one project. None
of that is visible from GitHub search, and `git diff` can't help because
you'd need to already know which two files to compare.

SkillVariants is **not a registry** ("what Skills can I install?") — it
answers a different question: *what happened to this Skill as different
repositories adapted it?*

## Web explorer

A static explorer over the three validated studies (home → study → motif →
compare) is in [`web/`](web/) — precomputed data, no backend, no auth.
See [`docs/web-explorer.md`](docs/web-explorer.md).

## Commands

```bash
skillvariants inspect  <url>            # frontmatter, body stats, signals
skillvariants related  <url> [--mode mutations|closest] [--json]
skillvariants evidence <url> --json     # agent-facing evidence payload
skillvariants compare  <url-a> <url-b>  # similarity + structural changes + diff
skillvariants study-*                   # persistent study runtime (for agents)
```

- `related --mode mutations` (default) shows the archetype map above.
- `related --mode closest` is pure textual-nearest order after exact-copy
  collapsing — deliberately no story logic.
- All commands support `--json`; stdout is clean JSON, warnings go to stderr.

## How it works

Deterministic pipeline, fully inspectable:

1. same-name code search on GitHub (`"name: x" filename:SKILL.md`)
2. normalized SHA-256 collapse of exact copies (body-only variants kept separate)
3. conservative relatedness gate (name match requires content corroboration)
4. mutation feature vectors (plain regex + RapidFuzz)
5. near-copy grouping (union-find ≥ 0.90 body ratio + hub partition)
6. archetype classification by fixed signal rules
7. per-archetype representative scoring with absorber/deletion/placeholder penalties
8. agent semantic layer: PASS A group analysis → behavior-equivalence
   consolidation → per-group verification → deterministic acceptance

No LLM inside the engine; the agent layer is your own coding agent.

## What it does not claim

No ancestry proof ("original", "copied from"), no census ("all variants"),
no quality-by-frequency, no security judgment. Agent interpretations may
vary; the semantic validation to date is internal with a same-model caveat.
See [`docs/limitations.md`](docs/limitations.md).

## Validation

Validated on three high-copy skill families, five known adaptation anchors,
and 243 human-audited mutation groups. All five anchors were found and
correctly classified; the consolidation guardrail reduced over-merge from
26% to 0% with 100% two-run stability. Methodology:
[`research/validation-summary.md`](research/validation-summary.md),
[`research/agent-benchmark/v1/`](research/agent-benchmark/v1/).

## Contributing

False-positive and misclassification reports are the most valuable
contributions — see [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Credits / research inspiration

Inspired by public Agent Skills ecosystems including
[obra/superpowers](https://github.com/obra/superpowers) and
[anthropics/skills](https://github.com/anthropics/skills).

Third-party test fixture redistribution was reviewed separately.
No `anthropics/skills` Skill text is bundled because no repository
license was found at audit time. See [`research/fixture-audit.md`](research/fixture-audit.md).

## License

[Apache-2.0](LICENSE)
