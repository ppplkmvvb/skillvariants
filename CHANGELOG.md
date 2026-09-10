# Changelog

All notable changes to SkillVariants are documented here.

## 0.3.0 — unreleased

- Local-file inspect and compare without GitHub credentials; JSON comparisons include paired raw-line hunks, source hashes and explicit truncation.
- Immutable GitHub source capture, refresh/offline controls, bounded cache freshness, slash-containing ref resolution and actionable acquisition errors.
- Evidence schema 2 keeps distinct normalized candidates separate and discloses fetch, gate, duplicate and occurrence denominators.
- Experimental semantic claims require ADDED/REMOVED/MODIFIED/UNCHANGED direction and exact citations from both sources. Unresolved material remains visible.
- Persisted task membership, complete verifier coverage, explicit cluster suppression, source/corpus identity, owned snapshots, cross-process locks, crash recovery and stale-task rejection.
- Engine-generated reports retain citations and counts. Optional analyst prose is stored separately. Empty studies produce readable artifacts.
- Actual text similarity prevents equal-length approval reversals from being treated as unchanged by the previous length shortcut.
- Original example explorer, current English/Chinese documentation, separate evaluation inputs/answers/predictions and corrected historical claims.
- Retained fixture licenses and provenance; removed three unused captures with unresolved redistribution provenance.
- Linux/Windows CI gates tested wheel, sdist and separate Agent Skill artifacts before publishing.

Migration: old studies are read-only under the new internal protocol; start a new study. Global source options precede command names. `--base-dir` is a workspace root. Semantic groups/counts are not comparable to legacy fuzzy groups. Install the Agent Skill and CLI from the same revision.

Historical correction: the v0.2 benchmark replay and copied stability run did not establish independent accuracy. The claims below record the old release description and must not be used as current validation evidence.

## 0.2.0

- Agent Study Runtime: persistent, resumable study sessions
  (study-start / study-next / study-submit / study-report)
- Installable Agent Skill with a six-step runtime-driven workflow
- Agent-facing evidence JSON (`skillvariants evidence --json`)
- Semantic consolidation guardrail: behavior signatures, strict invariants,
  verifier task and deterministic acceptance (historical replay metrics withdrawn as independent evidence)
- Recurring adaptation reports with real source implementations
- Static Web explorer over three historical studies (subsequently retired from the public example data)
- CLI UX: cleaner help/errors, PowerShell-safe examples

## 0.1.1

- Fix public source-install repository URL
- Clarify third-party fixture licensing language
- Publish installable PyPI package

## 0.1.0

- Inspect public Agent Skills
- Find related variants across GitHub
- Collapse exact and near copies
- Group adaptations into mutation archetypes
- Compare structural and textual changes
- Export deterministic JSON
