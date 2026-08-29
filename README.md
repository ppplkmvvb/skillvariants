# SkillVariants

**See how Agent Skills change across GitHub.**

Paste any public `SKILL.md` URL. SkillVariants finds related copies and
adaptations, groups them by mutation pattern, and shows representative
changes — deterministically, without an LLM.

```bash
uvx skillvariants related \
  https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md
```

Real output (abridged; full version in [`examples/systematic-debugging.txt`](examples/systematic-debugging.txt)):

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
  shell commands +0/-3

Archive228/loopkit
  relatedness: 0.54
  length changed by -85%
  ...

ROUTING SPECIALIZATIONS
8 groups · 18 unique variants · 22 occurrences
─────────────────────────────────────────────
bg-szy/TOP-SKILLS
  relatedness: 0.82
  new routing-boundary language
  +6 cross-skill references

WORKFLOW SPECIALIZATIONS
30 groups · 40 unique variants · 49 occurrences
─────────────────────────────────────────────
arn0ld87/skills-public-archive
  workflow structure reworked (+13/-15 sections)
```

## Why this exists

Agent Skills get copied between repositories constantly — and the copies are
rarely identical. They get **compressed into checklists**, wrapped in thin
redirects, rerouted to sibling skills, or specialized for one project. None of
that is visible from GitHub search, and `git diff` can't help because you'd
need to already know which two files to compare.

SkillVariants does the part diff tools can't:

```text
one target Skill
   ↓  discover related variants across repositories
   ↓  collapse exact and near copies
   ↓  classify adaptation patterns (mutation archetypes)
   ↓  select representative variants per archetype
   ↓  show deterministic evidence for each
```

It is **not a registry** ("what Skills can I install?") — it answers a
different question: *what happened to this Skill as different repositories
adapted it?*

## Quick start

Requires Python 3.11+.

```bash
# zero-install (if published on PyPI)
uvx skillvariants related <SKILL.md-url>

# or
pipx install skillvariants
skillvariants related <SKILL.md-url>

# from source
pipx install git+https://github.com/ppplkmvvb/skillvariants.git
```

GitHub Code Search needs authentication, either:

```text
export GITHUB_TOKEN=...
```

or an existing `gh` CLI login (`gh auth login`). If neither is present you get
a short, actionable error. Fetched files are cached under `.cache/skillvariants/`
(gitignored, no tokens stored, no telemetry).

## Use it from your agent

SkillVariants Core finds and structures the evidence. The Skill lets your
agent interpret it.

Install the bundled Agent Skill (`skills/skillvariants/`) into your agent's
skills directory and prompt it:

```text
Study how this Skill has been adapted across GitHub:
https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md
```

The agent runs the deterministic pipeline, analyzes mutation groups, and
presents recurring adaptation motifs with real source links — under strict
interpretation rules (observed fact vs interpretation vs user-specific
suggestion, no ancestry claims, no frequency-as-quality). Details and
validation status: [`docs/agent-skill.md`](docs/agent-skill.md).

## Mutation archetypes

| Archetype | What it looks like |
|---|---|
| Compact rewrite | Same intent, drastically shorter; methodology reduced to a checklist |
| Expanded guidance | Original plus added sections/examples/environment rules |
| Routing specialization | Adds routing boundaries: "do not use X here", "owns Y", cross-skill references |
| Workflow specialization | Phases restructured; project-specific process steps inserted |
| Project specialization | Repo-specific paths, migration notes, product names |
| Compatibility wrapper | Tiny body redirecting to a canonical path |

Archetypes are heuristic descriptive categories, not a formal taxonomy and not
provenance claims. Details: [`docs/archetypes.md`](docs/archetypes.md).

## Commands

```bash
skillvariants inspect  <url>            # frontmatter, body stats, signals
skillvariants related  <url> [--mode mutations|closest] [--json]
skillvariants evidence <url> --json     # agent-facing evidence payload
skillvariants compare  <url-a> <url-b>  # similarity + structural changes + diff
```

- `related --mode mutations` (default) shows the archetype map above.
- `related --mode closest` is pure textual-nearest order after exact-copy
  collapsing — deliberately no story logic.
- `--json` on every command emits machine-readable output with per-result
  evidence strings.

## How it works

Deterministic pipeline, fully inspectable:

1. same-name code search on GitHub (`"name: x" filename:SKILL.md`)
2. normalized SHA-256 collapse of exact copies (body-only variants kept separate)
3. conservative relatedness gate (name match requires content corroboration;
   canonical pointers are accepted direct evidence)
4. mutation feature vectors (length/heading/command/reference deltas via plain regex + RapidFuzz)
5. near-copy grouping (union-find ≥ 0.90 body ratio plus a hub partition for star-shaped clone fields)
6. archetype classification by fixed signal rules
7. per-archetype representative scoring with penalty terms for absorber files, deletion-only rewrites, and placeholder templates

No LLM, no embeddings, no vector database. Every score emits its own evidence.

## What it does not claim

SkillVariants detects relationships and differences. It does **not** prove
ancestry — never "original", "copied from", or "forked from". Search results
are not a complete census of GitHub. It is not a security scanner and makes no
safety statement about any Skill. See [`docs/limitations.md`](docs/limitations.md).

## Validation

We validated the deterministic pipeline on three high-copy Skill families,
five known adaptation anchors, and 34 displayed representatives. In that
validation set, all five anchors were found and assigned the expected
archetype; human review marked 34/34 displayed representatives as correct or
arguable rather than clearly wrong; reruns produced byte-identical JSON.
Methodology and numbers: [`research/validation-summary.md`](research/validation-summary.md).
Three families are a validation set, not a census of the ecosystem.

## Limitations

Known and documented up front: taxonomy overlap (workflow vs project),
GitHub search coverage gaps, placeholder/template edge cases as
representatives, heuristic relatedness, and changing upstream repos. Full
list: [`docs/limitations.md`](docs/limitations.md). Production backlog items
live there too — please don't expect v0.1 to have solved them.

## Contributing

False-positive reports and misclassification cases are the most valuable
contributions — see [`CONTRIBUTING.md`](CONTRIBUTING.md) and the
*Classification / false-positive* issue template.

## Credits / research inspiration

Inspired by public Agent Skills ecosystems including
[obra/superpowers](https://github.com/obra/superpowers) and
[anthropics/skills](https://github.com/anthropics/skills).

Third-party test fixture redistribution was reviewed separately.
No `anthropics/skills` Skill text is bundled because no repository
license was found at audit time. See [`research/fixture-audit.md`](research/fixture-audit.md).

## License

[Apache-2.0](LICENSE)
