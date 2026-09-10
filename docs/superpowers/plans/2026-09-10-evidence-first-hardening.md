# Evidence-first hardening implementation plan

> For agentic workers: execute the owned tasks below with test-first changes, independent review, and integration verification. The user has authorized parallel subagents using GPT-6 Astra with high reasoning. Historical phase instructions do not override this plan.

**Goal:** Make SkillVariants a trustworthy, useful, maintainable open-source tool for finding and understanding changes to Agent Skills, with a small deterministic core and an explicitly experimental semantic study workflow.

**Architecture:** Preserve the Python CLI and static explorer. Source snapshots and paired differences are the authority; semantic claims are optional interpretations and must cite both sides. Persist complete task membership and source identity so interrupted, rejected, or repeated work cannot silently change coverage.

**Tech Stack:** Python 3.11+, Typer, HTTPX, PyYAML, pytest, plain HTML/CSS/JavaScript, GitHub Actions.

## Product contract

- Primary user: a Skill maintainer comparing adaptations before deciding what to change.
- Default outcome: a bounded shortlist with exact differences, source identity, counts with explicit denominators, and limitations.
- Optional outcome: an experimental study of observed behavioral changes. Repetition is neither quality nor independent adoption.
- No fabricated evaluation, users, endorsements, star counts, or ancestry claims.
- Every task member is either analyzed or explicitly unresolved. COMPLETE always has readable artifacts.
- Success measures: useful-difference discovery time, relevance of the shortlist, direction-of-change accuracy, evidence support, task coverage, reproducibility, and cost visibility.
- GitHub popularity is an outcome to observe, not a promised release criterion. Prepare useful examples, good documentation, contribution paths, and a truthful launch kit.

## Workspace and ownership

Work in `G:/PROJECT/skillvariants`, branch `codex/evidence-first-hardening`. Preserve the pre-existing untracked `research/codex-independent-audit/`. Do not edit unrelated parent-repository files. `G:/PROJECT/agent` will receive an index of the current contract; `G:/PROJECT/skilldiff-spike` will be explicitly frozen as historical research.

| Workstream | Owned paths | Integration boundary |
|---|---|---|
| Runtime | `src/skillvariants/study/`, `src/skillvariants/consolidation.py`, runtime/consolidation tests | `StudyStore(base_dir)` treats base_dir as workspace root; `.skillvariants/studies` is appended once |
| Source and evidence | `github.py`, `parser.py`, `cli_helpers.py`, new `comparison.py`, source/parser/evidence tests | Keep `fetch_text` compatible; expose `compare_documents(a, b)` returning JSON-safe paired diff evidence |
| CLI | `cli.py`, CLI/production tests | Use the shared store; consume `compare_documents`; support documented JSON flags |
| Integration | ranking/similarity, fixtures, web/scripts, packaging/CI, documentation, evaluation | Root agent reviews all changes and tests the actual entry points |

## Task 1: Runtime integrity

- [x] Add failing tests for partial Pass A, >8 verification members, wrong task identity, early final report, same content from different repositories, changed batch size on resume, upstream forced resubmission, invalid study paths, and a no-motif completed report.
- [x] Run `python -m pytest tests/test_study_runtime.py -q` and record the expected failures.
- [x] Enforce complete response membership and persisted dispatch membership. Use source identity plus content and protocol version in study identity. Invalidate dependent artifacts and fingerprints after accepted upstream replacement. Reject incomplete finalization.
- [x] Verify every original proposed group across bounded verifier tasks. Enforce prechecks instead of silently discarding their results; suppress unsupported oversized clusters explicitly if splitting is not implemented.
- [x] Ensure empty and rejected studies emit report.json and report.md; expose coverage and unresolved counts.
- [x] Require typed change direction and paired evidence for new semantic claims, with explicit abstention when evidence is insufficient. Retain old artifacts as legacy, never silently treat them as newly validated.
- [x] Run runtime and consolidation tests, then report changed interfaces to integration.

## Task 2: Sources and comparisons

- [x] Add failing HTTPX-backed tests for stale cache refresh, immutable source metadata, network failures, unresolved branches, and branch names containing slashes; add tests calling the production evidence builder directly.
- [x] Create `compare_documents(a, b)` in `comparison.py`; its JSON-safe result includes `unified_diff`, line-numbered paired hunks, and explicit truncation metadata. It must not infer semantic direction from token presence.
- [x] Correct diff-header filtering and count denominators. Preserve duplicate occurrences and source metadata rather than confusing unique content with independent repositories.
- [x] Capture raw content hash and timestamp; use resolved immutable references when available. Never substitute a guessed main branch after failure. Bound/refresh mutable caches and keep offline cache state visible.
- [x] Remove the circular import from evidence assembly into CLI state.
- [x] Run source, parser and evidence tests and report the exact comparison/snapshot contract.

## Task 3: CLI contract

- [x] Reproduce failures through Typer's real command entry points before changing code: documented JSON flags, custom base directory, missing study, authentication failure, YAML date serialization, and GBK output.
- [x] Make study commands use a consistent workspace-root base directory and StudyStore lookup. Emit actionable errors with a nonzero exit code and no secondary exception.
- [x] Add actual paired differences to `compare --json` through the shared comparison module; preserve existing a/b/similarity/classification fields for consumers.
- [x] Accept local files for comparison/inspection if this can be done without duplicating source logic, enabling a credential-free first-use example.
- [x] Run CLI/production regressions and an isolated command invocation.

## Task 4: Deterministic ranking and regression evidence

- [x] Add an approval-rule reversal regression showing that important text changes cannot be called identical or hidden in the low-change hub merely because name and length match.
- [x] Improve the textual component and hub predicate conservatively; retain documented heuristic limits and existing useful anchors.
- [x] Replace unsupported upstream fixtures with original synthetic cases, verify tracked filenames and distribution contents, and correct the fixture audit statements.
- [x] Introduce a reproducible evaluation harness with separate inputs, evaluator answers, predictions and scoring. Include abstention and coverage. Mark historical replay benchmarks as replay, not independent quality evidence.
- [x] Run genuinely independent analysis on held-out cases using an agent without evaluator answers; report errors as well as aggregate results.

## Task 5: Product, explorer and release

- [x] Rewrite README and current contract around the maintainer task, real quickstart, evidence example, limitations, experimental study status, and installation of the Agent Skill.
- [x] Replace misleading showcased claims with verified paired examples. Validate exported JSON schema and browser layout at desktop and 390px width.
- [x] Fix deploy ref update to PATCH and eliminate broad exception swallowing. Do not deploy until content and integration validation finish.
- [x] Validate the installed wheel locally; configure fixture/distribution checks and an end-to-end offline study in Linux/Windows CI. Gate release on those checks. Remote execution is tracked by the PR.
- [x] Add a concise architecture guide, contribution workflow, realistic roadmap, changelog, and an evidence-backed launch kit. Avoid empty governance files or invented adoption statistics.
- [x] Review the complete diff, run the full suite and build, inspect generated artifacts, and verify all user-facing commands before commit or any external release action.

## Verification commands in this workspace

The original virtualenv was unusable. A new isolated `.venv-dev` environment is now provisioned with the project's development dependencies. Run without a source-path override:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
.venv-dev/Scripts/python.exe -B -m pytest -p no:cacheprovider --basetemp .test-tmp-verification -q
```

Use separate temporary roots per worker to avoid cleanup races. Build and installed-wheel checks remain separate release gates. Pytest discovers only `tests/`, so unrelated historical caches cannot become part of the test suite.

## Review checkpoints

- [x] Unit regressions fail before fixes and pass afterward.
- [x] Integration confirms no silent dropped groups and valid reports for empty results.
- [x] Every published claim is backed by a paired source or explicitly marked interpretation.
- [x] Documentation commands run from an installed artifact.
- [x] Current changes are independently reviewed, committed coherently, and ready for a concrete release decision.
