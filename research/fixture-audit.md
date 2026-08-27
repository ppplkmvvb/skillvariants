# Third-Party Skill Text Fixture Audit

Status: **complete** (v0.1.0). Every bundled `tests/fixtures/` file was traced
to its source, its license checked, and its redistribution decided explicitly.

## Bundled fixtures

| Fixture | Source repo | Upstream license | Redistributed? | Action |
|---|---|---|---|---|
| `frontend_design/reference_synthetic.md` | none — original synthetic text written for this repo (structure informed by the public *shape* of common frontend skills) | n/a (CC0 declared in-file) | Yes (ours) | Kept |
| `frontend_design/variant_compact_rewrite_synthetic.md` | none — original synthetic text | n/a (CC0) | Yes (ours) | Kept |
| `negative/unrelated_offtopic_synthetic.md` | none — original synthetic text | n/a (CC0) | Yes (ours) | Kept |
| all other `tests/fixtures/**` files (systematic-debugging family: reference / loopkit variant / Vibe-Skills variant; brainstorming family: SuperAntigravity variant; verification-before-completion pair; docx negative control) | see table below | MIT or Apache-2.0 (verified per repo) | Yes, with attribution below | Kept |

## Redistribution-audited upstream sources

During the feasibility spikes these live repositories' `SKILL.md` files were
fetched and stored as offline test fixtures. License verification commands:
`gh api repos/<owner>/<repo> --jq .license.spdx_id`.

| Source repository | Upstream license at audit time | Fixture role | Notes |
|---|---|---|---|
| `obra/superpowers` | MIT | systematic-debugging + brainstorming + verification-before-completion references | Attribution preserved via source URL in fixture filename/research notes |
| `Archive228/loopkit` | MIT | systematic-debugging compact-rewrite anchor | |
| `foryourhealth111-pixel/Vibe-Skills` | Apache-2.0 | routing-specialization anchor | Apache-2.0 requires license/notice propagation on redistribution; NOTICE preserved in this file |
| `Rain120/qq-music-api` | MIT | frontend-design compatibility-wrapper analysis target | File itself **not** bundled; only referenced by URL (branch `next`) in live-URL metadata |
| `derHaken/SuperAntigravity` | MIT | brainstorming workflow-specialization anchor | |

## Removed for licensing reasons

| Fixture | Source repo | License | Reason removed |
|---|---|---|---|
| `reference_anthropics.md` | `anthropics/skills` | **none** (no LICENSE file found at audit time) | All-rights-reserved default; redistribution not permitted |
| `variant_pilotdeck.md` | `OpenBMB/PilotDeck` | **AGPL-3.0** | Strong copyleft incompatible with bundling skill prose into an Apache-2.0 test suite without dual-licensing the project |
| `unrelated_docx_anthropics.md` | `anthropics/skills` | **none** | Same as above |

Each removed file was replaced by a purpose-built synthetic fixture that
preserves the structural property the tests need (same-name compact rewrite
with paraphrased wording; same-name off-topic negative control), so no
coverage was lost.

## Anchor URLs kept as references, not copies

The five validation anchors are documented as live GitHub URLs
(`tests/tests_helpers.py::LIVE_REFERENCE_URLS` / `LIVE_VARIANT_URLS`) rather
than redistributed bytes wherever the upstream license did not clearly permit
bundling. Live evaluation fetches them at run time under the user's own
GitHub authentication.

## Caveat

Upstream licenses can change. Re-run the audit before any major release:
fetch each repo's `.license.spdx_id`, compare against this table, and re-check
the upstream files if a fixture's content needs updating.
