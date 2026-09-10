# The approval checkpoint

Three original teaching examples, authored for SkillVariants. They are not sampled GitHub adaptations or observations of agent execution.

| Example | Target | Variant | Focused reading |
|---|---|---|---|
| Added | [source](added/target/SKILL.md) | [source](added/variant/SKILL.md) | A new approval requirement appears before implementation |
| Preserved | [source](preserved/target/SKILL.md) | [source](preserved/variant/SKILL.md) | The same requirement is expressed in different words |
| Reversed | [source](reversed/target/SKILL.md) | [source](reversed/variant/SKILL.md) | Implementation moves before the request for approval |

From the repository root with the CLI installed:

```bash
skillvariants compare examples/approval-gate/reversed/target/SKILL.md examples/approval-gate/reversed/variant/SKILL.md --json
```

The CLI computes the diff, raw hashes and paired line numbers. The interpretations above are authored explanations. In the experimental study protocol, preserved maps to UNCHANGED and reversed to MODIFIED.

The [static explorer](../../web/index.html) renders the same files via the production comparison engine. Regenerate with `python scripts/export_web_data.py` and check freshness with `--check`.
