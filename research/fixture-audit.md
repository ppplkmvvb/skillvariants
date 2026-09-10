# Offline fixture provenance audit

As of 2026-09-10, the offline suite contains **11 Skill text fixtures**: eight historical third-party captures and three original synthetic fixtures. Supporting manifests, license files and notice text are additional files, not part of that count.

The current inventory and raw-byte SHA-256 values are recorded in [`tests/fixtures/SOURCES.json`](../tests/fixtures/SOURCES.json). License texts and the Vibe-Skills notice are retained under [`tests/fixtures/licenses/`](../tests/fixtures/licenses/). This audit describes those repository records; no fresh remote license lookup was performed while writing this correction.

## Retained fixture inventory

| Fixture under `tests/fixtures/` | Recorded source | Recorded license context |
|---|---|---|
| `systematic_debugging/reference_superpowers.md` | `obra/superpowers` | MIT |
| `brainstorming/reference_superpowers.md` | `obra/superpowers` | MIT |
| `verification_before_completion/reference_superpowers.md` | `obra/superpowers` | MIT |
| `systematic_debugging/variant_loopkit.md` | `Archive228/loopkit` | MIT |
| `frontend_design/variant_qqmusicapi.md` | `Rain120/qq-music-api`, branch `next` | MIT |
| `brainstorming/variant_superantigravity.md` | `derHaken/SuperAntigravity` | MIT |
| `verification_before_completion/variant_superantigravity.md` | `derHaken/SuperAntigravity` | MIT |
| `systematic_debugging/variant_vibeskills.md` | `foryourhealth111-pixel/Vibe-Skills` | MIT AND Apache-2.0; both license texts and the recorded notice retained |
| `frontend_design/reference_synthetic.md` | Original synthetic text | CC0-1.0 declared in fixture |
| `frontend_design/variant_compact_rewrite_synthetic.md` | Original synthetic text | CC0-1.0 declared in fixture |
| `negative/unrelated_offtopic_synthetic.md` | Original synthetic text | CC0-1.0 declared in fixture |

The QQ Music compatibility-wrapper fixture is bundled. Earlier statements that it existed only as URL metadata were incorrect. The Vibe-Skills notice is a separate retained notice file; this prose audit is not a substitute for that notice.

## What the records establish and what is missing

The manifest identifies the exact bundled bytes, their recorded source URLs and the license/notice files retained for those sources. It records license retrieval on 2026-09-10, raw hashes for the retained license texts and available Git blob identifiers.

All historical Skill captures have `capture_commit: null`. Their original capture commits are unavailable. A mutable branch URL and a later repository license retrieval cannot reconstruct the historical per-file state with certainty. Accordingly, this audit does **not** claim that every fixture was traced to an immutable capture or that historical provenance is complete. The local raw hashes permit reproducible tests against the bundled bytes, not reconstruction of unknown upstream capture commits.

Preserve the manifest and applicable license/notice material when retaining these captures. For future captures, record the immutable source commit, exact path, raw content hash, retrieval time and applicable file-level license/notice context at capture time.

## Removed unused historical captures

The hardening change removes these three unused raw fixtures:

- `frontend_design/reference_anthropics.md`
- `frontend_design/variant_pilotdeck.md`
- `negative/unrelated_docx_anthropics.md`

The previous audit gave unsupported or oversimplified license explanations for these files. Those explanations are withdrawn. Their removal is a repository provenance and fixture-maintenance decision; this document does not infer a repository-wide license from missing historical metadata or assert blanket incompatibility between license families.

The three retained synthetic fixtures exercise the current compact-rewrite and unrelated-content controls. Their existence does not demonstrate that every historical behavior of the removed files has equivalent coverage. Current coverage is established by the tests that actually run.

## Evaluation and distribution scope

Historical upstream fixtures are regression inputs, not an independently sampled benchmark. The new original synthetic evaluation corpus has separate provenance and answer handling, documented in [`docs/evaluation.md`](../docs/evaluation.md).

This audit concerns `tests/fixtures/`. It makes no blanket claim about the provenance of historical research exports, current explorer content, or built package contents; those artifacts require their own checks. In particular, old research metrics should not be promoted as independent accuracy evidence merely because the underlying fixture bytes have a recorded hash.
