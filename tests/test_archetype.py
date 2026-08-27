"""Final-spike tests (spec section 21): symmetric normalization, absorber
resistance, archetype buckets, representative quality, anchors, determinism."""
from __future__ import annotations

import io
import json
import math

from rich.console import Console

from skillvariants.cli import _build_variant_pool
from skillvariants.github import CodeHit
from skillvariants.ranking import (
    build_archetype_map,
    normalized_length_change,
)

from conftest import (
    LOOPKIT_SD,
    SUPERPOWERS_SD,
    VIBESKILLS_SD,
    FakeGitHubClient,
    fixture_text,
)
from tests_helpers import build_test_pool, doc_text, TARGET_BODY


class TestSymmetricLengthNormalization:
    def test_double_equals_half(self) -> None:
        assert math.isclose(
            normalized_length_change(100, 200),
            normalized_length_change(200, 100),
        )
        assert math.isclose(
            normalized_length_change(1000, 500),
            normalized_length_change(500, 1000),
        )

    def test_quadruple_equals_quarter(self) -> None:
        assert math.isclose(
            normalized_length_change(100, 400),
            normalized_length_change(400, 100),
        )

    def test_ten_x_beats_two_x(self) -> None:
        assert normalized_length_change(100, 1000) > normalized_length_change(100, 200)

    def test_capped_at_one(self) -> None:
        assert normalized_length_change(10, 10_000_000) == 1.0


TARGET_URL = "https://github.com/test/target/blob/main/skills/sample/SKILL.md"


def _debugging_family_pool():
    files = {
        SUPERPOWERS_SD: fixture_text("systematic_debugging/reference_superpowers.md"),
        LOOPKIT_SD: fixture_text("systematic_debugging/variant_loopkit.md"),
        VIBESKILLS_SD: fixture_text("systematic_debugging/variant_vibeskills.md"),
    }
    hits = [
        CodeHit(repo=LOOPKIT_SD[0], path=LOOPKIT_SD[1], default_branch=LOOPKIT_SD[2], sha="", api_url=""),
        CodeHit(repo=VIBESKILLS_SD[0], path=VIBESKILLS_SD[1], default_branch=VIBESKILLS_SD[2], sha="", api_url=""),
    ]
    url = ("https://github.com/obra/superpowers/blob/main/"
           "skills/systematic-debugging/SKILL.md")
    client = FakeGitHubClient(files=files, hits=hits)
    return _build_variant_pool(url, cache_dir=None, max_pages=1, client=client)


def absorber_pool():
    honest = doc_text(
        TARGET_BODY + "\n## Extended Examples\nAdded worked examples.\n"
        "## Extra Checklist\nMore actionable guidance.\n" * 4
    )
    absorber = doc_text(
        TARGET_BODY + "\n\n" + ("totally unrelated filler paragraph about orchids.\n" * 250)
    )
    return build_test_pool({
        ("honest/repo", "e/SKILL.md"): honest,
        ("absorber/repo", "a/SKILL.md"): absorber,
    })


class TestAbsorberResistance:
    def test_absorber_does_not_top_expanded_guidance(self) -> None:
        pool = absorber_pool()
        buckets, _ = build_archetype_map(pool["pool"])
        expanded = next(b for b in buckets if b.archetype == "expanded-guidance")
        top_rep = expanded.ranked_groups[0].representative
        assert top_rep.repo == "honest/repo", (
            f"expected honest expansion first, got {top_rep.repo}"
        )
        # sanity: the absorber is really huge and incoherent
        from skillvariants.similarity import score_similarity
        t = pool["pool"][0]  # any row; use features of the absorber directly
        rows = {r.repo: r for r in pool["pool"]}
        ab = rows["absorber/repo"]
        assert ab.mutation_features.length_delta_ratio > 2.0
        assert ab.mutation_features.full_text_coherence < 0.30


COMPACT_STRUCTURED = doc_text(
    "# Sample\nShort loop: investigate, reproduce, fix, verify.\n"
    "Stop after three failed hypotheses.\n## Loop\n1. read error\n2. fix\n"
)
COMPACT_DELETION_ONLY = doc_text("# Sample\nDo the work carefully before changing anything.")


class TestRepresentativeSelection:
    def test_structured_compression_beats_deletion_only(self) -> None:
        pool = build_test_pool({
            ("deletion/repo", "d/SKILL.md"): COMPACT_DELETION_ONLY,
            ("structured/repo", "s/SKILL.md"): COMPACT_STRUCTURED,
        })
        buckets, _ = build_archetype_map(pool["pool"])
        compact = next(b for b in buckets if b.archetype == "compact-rewrite")
        reps = [g.representative.repo for g in compact.ranked_groups[:3]]
        assert reps[0] == "structured/repo", f"reps={reps}"


class TestBucketRendering:
    def test_three_archetypes_render_as_separate_sections(self) -> None:
        from skillvariants.cli import _build_mutations_payload
        from skillvariants.render import render_mutations

        near_copy = doc_text(TARGET_BODY.replace("Run git commands", "Run git cli"))
        wrapper = doc_text(
            "Compatibility wrapper; resolve the canonical definition.\n",
            extra_fm="\ncanonical_skill: ../../skills/sample/SKILL.md",
        )
        routing = doc_text(
            TARGET_BODY + "\n## Routing Boundary\nDo not use the audit skill; route to the reporting skill.\n"
        )
        compact = doc_text("# Sample\nShort loop: investigate, reproduce, fix, verify. Stop after three failed hypotheses.\n")
        pool = build_test_pool({
            ("clone/repo", "a/SKILL.md"): near_copy,
            ("wrap/repo", "w/SKILL.md"): wrapper,
            ("route/repo", "r/SKILL.md"): routing,
            ("compact/repo", "c/SKILL.md"): compact,
        })
        payload = _build_mutations_payload(pool, limit=3)
        buffer = io.StringIO()
        console = Console(file=buffer, width=140, force_terminal=False)
        render_mutations("sample", 4, payload, console=console)
        text = buffer.getvalue()
        for expected in (
            "COMPACT REWRITES",
            "ROUTING SPECIALIZATIONS",
            "COMPATIBILITY WRAPPERS",
        ):
            assert expected in text, f"missing section header {expected!r}"


class TestAnchorRegressions:
    def test_loopkit_and_vibeskills_are_found_related_and_typed(self) -> None:
        pool = _debugging_family_pool()
        by_repo = {r.repo: r for r in pool["pool"]}
        loopkit = by_repo["Archive228/loopkit"]
        vibe = by_repo["foryourhealth111-pixel/Vibe-Skills"]
        assert loopkit.relatedness >= 0.33 and vibe.relatedness >= 0.33
        assert loopkit.classification.primary == "compact-rewrite"
        assert vibe.classification.primary == "routing-specialization"

    def test_fulltext_coherence_feature_present(self) -> None:
        pool = _debugging_family_pool()
        for row in pool["pool"]:
            assert 0.0 <= row.mutation_features.full_text_coherence <= 1.0
            assert 0.0 <= row.mutation_features.symmetric_length_change <= 1.0


class TestJsonDeterminism:
    def test_repeated_pipeline_run_is_byte_identical(self) -> None:
        da = json.dumps(self._payload(), sort_keys=True, ensure_ascii=False)
        db = json.dumps(self._payload(), sort_keys=True, ensure_ascii=False)
        assert da == db

    def _payload(self):
        pool = _debugging_family_pool()
        buckets, summary = build_archetype_map(pool["pool"])
        simplified = {
            "counts": summary,
            "archetypes": [
                {
                    "type": bucket.archetype,
                    "group_count": len(bucket.ranked_groups),
                    "groups": [
                        {
                            "repo": g.representative.repo,
                            "primary": g.dominant_type(),
                            "members": sorted(m.repo for m in g.members),
                            "relatedness": round(g.representative.relatedness, 6),
                        }
                        for g in bucket.ranked_groups
                    ],
                }
                for bucket in buckets
            ],
        }
        return json.loads(json.dumps(simplified))
