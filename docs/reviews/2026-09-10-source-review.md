# Final source and ranking review — 2026-09-10

Reviewed the integrated `github.py`, `parser.py`, `comparison.py`, `cli_helpers.py`, `ranking.py` and `similarity.py` for release-blocking source/count/evidence defects. This is a final integration review, not an independent reimplementation: the reviewer previously authored much of the source/evidence work. Evaluation gold and recorded predictions were not opened or revised in this review.

## P1 found by the live CLI and fixed: GitHub's missing-ref 422 response

The root coordinator's authenticated live inspect of `obra/superpowers` returned HTTP 422 with `No commit found for SHA: main/skills/systematic-debugging` for the first candidate branch/path prefix. The resolver previously treated only 404 as a missing prefix, so ordinary deep GitHub URLs failed before reaching the valid `main` reference.

An HTTPX regression reproduced that exact response and failed before the fix. The resolver now continues only for status 422 whose JSON message exactly identifies the requested nonexistent SHA/prefix. A separate regression verifies that a generic `Validation Failed` 422 is still surfaced immediately. Existing slash-ref behavior remains covered. This narrowly scoped production change was explicitly authorized after the otherwise read-only review began.

## P2 found and fixed: an already fetched immutable ref could not be reopened offline

**Location:** `src/skillvariants/github.py`, `fetch_document` cache-index lookup and final index write.

Fetching a mutable ref previously wrote the index only under the original input ref, even though the returned source and public URL use the resolved commit. A subsequent offline request using that emitted immutable source could not find the index, despite the correct raw snapshot already existing on disk.

**Reproduced through public APIs:** fetch `GitHubRef('example', 'skills', 'main', 'SKILL.md')` with an HTTPX transport resolving it to a 40-character commit; open a new `GitHubClient(cache, offline=True)`; call `fetch_document(first_document.source)`. It raises `Offline cache miss`. The raw snapshot exists, and reading the original `main` reference through the same offline client succeeds. Output is retained in `.test-tmp-source-review/offline-result.json`.

**Correction:** persist the same cache record under the resolved immutable ref as well as the requested mutable ref. The alias retains the original requested ref, resolved commit, path, raw-byte hash, and fetch timestamp. Refreshing a moving branch writes the new commit's alias while retaining the old commit's alias and raw snapshot. Two HTTPX regression tests reproduced the offline cache miss before this explicitly authorized fix: reopening an emitted immutable source with its original provenance, and reopening both immutable sources after a branch moves.

## Scope and residual uncertainty

No additional P1 blocker was confirmed in the reviewed modules. Existing tests exercise raw CRLF preservation, source hashes, cache integrity and freshness, unavailable refs, paired raw-line evidence, explicit truncation, gated count denominators, duplicate occurrence preservation, and ordered-text ranking regressions. These are deterministic regression checks, not proof of semantic equivalence or complete GitHub retrieval coverage.

Post-fix verification: 77 tests passed across `test_sources.py`, `test_parser.py`, `test_comparison.py`, `test_evidence.py`, `test_ranking.py`, `test_similarity.py`, and `test_source_cli.py` in the clean development environment. `git diff --check` reported no whitespace errors.

The only live-GitHub outcome used here is the root coordinator's reported 422 failure; the reviewer does not claim a separate successful live request. Near-copy browsing remains a textual heuristic, while the production semantic evidence builder retains every distinct normalized candidate. Whitespace normalization is explicitly a normalized-content identity, not raw-byte identity.
