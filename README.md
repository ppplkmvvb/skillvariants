# SkillVariants

**Find useful changes to Agent Skills. Read the evidence before you adopt them.**

SkillVariants helps Skill maintainers discover related `SKILL.md` files on GitHub, collapse copies, and compare the instructions that changed. Start with a shortlist and a paired diff. Use your coding agent for an optional, experimental study of behavioral changes.

[中文说明](README.zh-CN.md) · [Examples](examples/approval-gate/README.md) · [Architecture](docs/architecture.md) · [Evaluation](docs/evaluation.md) · [Contributing](CONTRIBUTING.md)

```diff
- Do not implement before the user approves the plan.
+ Implement the plan before asking for user approval.
```

Similar names and document lengths can hide an opposite instruction. The CLI preserves exact source text, hashes, line numbers, and explicit truncation. It does not decide whether an instruction is good for your workflow.

## Quickstart

Python 3.11+. From a checkout of **this revision**, install the CLI and compare the original examples:

```bash
python -m pip install .
skillvariants compare examples/approval-gate/reversed/target/SKILL.md examples/approval-gate/reversed/variant/SKILL.md
```

Local inspection and comparison need no GitHub account, token, or LLM service. Add `--json` for machine-readable paired hunks. The 0.3 changes documented here are under development; an older PyPI release does not contain them.

For your own files:

```bash
skillvariants inspect ./SKILL.md --json
skillvariants compare ./SKILL.md ./adapted/SKILL.md --json
```

To discover GitHub candidates, authenticate with `gh auth login` or set `GITHUB_TOKEN`, then:

```bash
skillvariants related https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md --mode closest
```

The command is on one line so it also works in PowerShell. GitHub search is bounded, requires authentication, and can miss renamed or unindexed files.

## Choose the smallest useful workflow

| You want to… | Use |
|---|---|
| Inspect metadata and structural signals | `inspect <url-or-file> --json` |
| Find related files to read | `related <url> --mode closest` |
| Browse heuristic categories of adaptations | `related <url> --mode mutations` |
| Check exactly what changed | `compare <url-or-file> <url-or-file> --json` |
| Export source-backed inputs for an agent | `evidence <url> --json` |
| Study recurring changes with your own agent | Experimental `study-*` workflow |

`closest` orders a weighted textual/structural similarity heuristic. `mutations` groups browsing results into heuristic archetypes; neither is a quality ranking. Semantic evidence keeps every distinct normalized candidate separate, so a representative cannot hide a different instruction.

Global source options go **before** the command:

```bash
skillvariants --refresh evidence <url> --json
skillvariants --offline evidence <url> --json
skillvariants --cache-max-age 3600 related <url>
```

The online cache expires after one hour by default. Offline mode uses only existing cached search results and source snapshots, with cache provenance in JSON. It fails when required data is missing.

## Optional agent studies

Copy [`skills/skillvariants/`](skills/skillvariants/) into your agent's Skill directory and use the CLI installed from this revision. The Agent Skill is a separate deliverable from the Python wheel.

Ask: “Find relevant adaptations of this Skill, compare the most useful candidates, and show both source passages.” Request a full study when recurring patterns matter.

The runtime dispatches bounded tasks, validates exact paired citations and change direction, records unresolved evidence, and computes coverage and recurrence. It stores hash-checked source snapshots inside each study. A changed corpus creates a new study; interrupted or concurrent writes cannot silently advance stale work.

**Semantic analysis is experimental.** Exact quotation checks prove that a quote exists, not that an agent's interpretation follows from it. A verifier pass is a separate task; model independence depends on how you run your agents. See the [workflow](docs/agent-skill.md) and [runtime contract](docs/agent-runtime.md).

## Read an example

The [static explorer](web/) presents three original examples: an approval checkpoint is added, preserved, or reversed. Each includes paired evidence, complete sources, a full diff, and a command to reproduce it.

```bash
python -m http.server 8769 --bind 127.0.0.1 --directory web
```

Open `http://127.0.0.1:8769`. These are authored teaching examples, not measurements of GitHub adoption. See [web development](docs/web-explorer.md).

## What is verified

Regression tests exercise the actual CLI, source cache, quotation checks, coverage, crash recovery, conflicting writers, report generation, and release artifacts. CI runs on Linux and Windows and tests the installed wheel separately.

The [evaluation protocol](docs/evaluation.md) separates inputs, expected answers, and external predictions. Historical replay benchmarks are preserved as research, with their limitations. Their old “0% over-merge” and “100% stability” numbers are **not independent model-quality evidence**.

There is no evidence yet that this tool saves maintainers time in representative real-world use. Useful contributions are difficult source pairs, incorrect change directions, and reports of decisions the tool helped or failed to support.

## Scope

No ancestry proof, exhaustive census, security certification, popularity ranking, or quality-by-frequency claim. Search, normalization, and ranking are heuristics. See [limitations](docs/limitations.md), [current product contract](docs/product-contract.md), and [roadmap](ROADMAP.md).

## Contribute

[Set up development](CONTRIBUTING.md), report a misleading comparison, or add a reproducible case. Include both sources, the instruction at issue, and the behavior you expected.

[Apache-2.0](LICENSE). Retained third-party test fixtures have their own licenses and provenance in [SOURCES.json](tests/fixtures/SOURCES.json) and the [fixture audit](research/fixture-audit.md). They are not bundled in the Python distributions.
