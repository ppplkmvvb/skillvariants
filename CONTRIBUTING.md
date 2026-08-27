# Contributing to SkillVariants

Thanks for helping improve the tool! The most valuable contributions are
**reports from real usage**, especially ones where the deterministic heuristics
get things wrong.

## What we especially want

- **False-positive relatedness reports** — a candidate that shows up as
  "related" but clearly is not. Include both URLs.
- **Archetype misclassification reports** — e.g. something labeled
  `compact-rewrite` that is really an expanded rewrite, or `workflow-`
  vs `project-specialization` confusion (known overlap, see docs/archetypes.md).
- **Representative-selection fixtures** — cases where a weak or misleading
  variant became the displayed representative for an archetype.
- **GitHub URL parsing fixes** — URL shapes we fail to parse.
- **Documentation improvements.**

Open a normal GitHub issue; use the *Classification / false-positive*
template when applicable.

## Local development

Requires Python 3.11+.

```bash
git clone https://github.com/ppplkmvvb/skillvariants.git
cd skillvariants
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e .
pytest
```

Optional full run against live GitHub data (needs auth):

```bash
export GITHUB_TOKEN=...   # or: gh auth login
skillvariants related \
  https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md
```

## Ground rules

- Deterministic only: no LLM calls, no embeddings, no network services beyond
  the GitHub API.
- Every score must stay explainable — if you add a signal, it needs evidence
  in the JSON output and a test.
- Respect third-party licenses: do not bundle new upstream Skill texts without
  updating `research/fixture-audit.md`.
