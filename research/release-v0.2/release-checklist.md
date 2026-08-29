# Release Checklist — v0.2.0

## Product gates

| Gate | Status |
|---|---|
| Agent: one natural-language request → autonomous study → final report → source links → follow-up compare | PASS (see agent-acceptance.md) |
| CLI: clean run, existing commands work, JSON contracts parse | PASS (see cli-acceptance.md) |
| Web: 3 real studies, motif → source → compare, static build | PASS (see web-acceptance.md) |
| Full tests green | PASS (127 passed) |
| CI green | PASS (main + tag workflows) |
| License audit green | PASS (see license-audit.md) |
| No suppressed motif leakage | PASS (release_qa.py) |
| No fake counts / no fabricated sources | PASS (counts from artifacts, URLs deterministic) |

## Docs gates

| Gate | Status |
|---|---|
| README first-run clear (uv prerequisite stated, not "zero-install") | PASS |
| Agent install clear (skills/skillvariants/ path + requirements) | PASS |
| Windows instructions clear (PowerShell examples) | PASS |
| Limitations explicit | PASS (docs/limitations.md + README section) |

## Publishing steps (executed after READY)

1. `git tag v0.2.0 && git push origin v0.2.0` → triggers `release.yml`
   → PyPI publish via Trusted Publishing
2. GitHub Release `SkillVariants v0.2.0` with release notes
3. GitHub Pages from `/web` for the explorer
4. Post-publish `uvx skillvariants` acceptance re-run

## Deliberately not in v0.2

Web live analysis, hosted LLM, accounts/OAuth, MCP, recommendation scores,
automatic Skill editing, PR generation, lineage claims.
