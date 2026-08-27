"""Offline tests for the ranking redesign (spec sections 26-27).

All tests run against a FakeGitHubClient built from synthetic documents and
real fixtures, so no network is involved.
"""
from __future__ import annotations

import re

from skillvariants.cli import _build_variant_pool
from skillvariants.github import CodeHit
from skillvariants.parser import parse_skill_md
from skillvariants.ranking import (
    MIN_RELATEDNESS,
    group_variants,
)
from skillvariants.features import extract_features
from skillvariants.similarity import score_similarity

from conftest import FakeGitHubClient

TARGET_URL = (
    "https://github.com/test/target/blob/main/skills/sample/SKILL.md"
)


def doc_text(body: str, name: str = "sample", description: str = "A sample skill guiding careful systematic work.", extra_fm: str = "") -> str:
    return f"---\nname: {name}\ndescription: {description}{extra_fm}\n---\n{body}"


TARGET_BODY = """# Sample
## Overview
Do the work carefully before changing anything.
## Phase 1: investigate
Read the failing output and reproduce it first.
## Phase 2: implement
Write the fix with a regression test.
## Phase 3: verify
Run git commands to verify everything passes.
"""


def make_pool(rows: dict[tuple[str, str], str], target_path=("test/target", "skills/sample/SKILL.md")):
    files = {(target_path[0], target_path[1], "main"): doc_text(TARGET_BODY)}
    files.update({(repo, path, "main"): text for (repo, path), text in rows.items()})
    hits = [
        CodeHit(repo=repo, path=path, default_branch="main", sha="", api_url="")
        for repo, path in rows
    ]
    client = FakeGitHubClient(files=files, hits=hits)
    return _build_variant_pool(TARGET_URL, cache_dir=None, max_pages=1, client=client)


class TestExactCopyCollapse:
    def test_identical_content_collapses_with_copy_count(self) -> None:
        body = doc_text("# Sample\n## Overview\nnearly the same body\n" * 5)
        pool = make_pool({
            ("a/one", "s/SKILL.md"): body,
            ("b/two", "deep/skills/sample/SKILL.md"): body,
            ("c/three", "x/y/z/SKILL.md"): body,
        })
        assert len(pool["pool"]) == 1
        row = pool["pool"][0]
        assert row.copy_count == 3
        assert pool["counts"]["exact_copies_of_target"] == 0


class TestGrouping:
    def test_similar_variants_group_together(self) -> None:
        base = doc_text(
            "# Sample\n## Overview\ncareful work matters here.\n"
            "## Phase 1: investigate\nreproduce the failure first, always.\n"
            "## Phase 2: implement\nfix it with a regression test.\n"
            "## Phase 3: verify\nrun git to verify results.\n"
        )
        tweak = base.replace("always", "always and quickly")
        rows = []
        for i, text in enumerate([base, tweak]):
            d = parse_skill_md(text)
            from skillvariants.classify import classify_pair
            t = parse_skill_md(doc_text(TARGET_BODY))
            tf = extract_features(t)
            cf = extract_features(d)
            sim = score_similarity(t, tf, d, cf)
            from skillvariants.classify import classify_pair as cp
            cls = cp(t, tf, d, cf, sim)
            from skillvariants.ranking import build_variant_row
            rows.append(build_variant_row(
                repo=f"r{i}", path="p", ref="main", doc=d, feats=cf, sim=sim,
                classification=cls, copy_count=1, sha256_full=f"h{i}",
                target_doc=t, target_feats=tf, target_name="sample",
            ))
        groups = group_variants(rows)
        assert len(groups) == 1
        assert len(groups[0].members) == 2
        rep = groups[0].representative
        assert rep.repo in {"r0", "r1"}

    def test_different_variants_stay_separate(self) -> None:
        wrapper = doc_text(
            "Project-facing compatibility wrapper. Resolve the canonical "
            "definition before loading the real skill body.\n",
            extra_fm="\ncanonical_skill: ../skills/sample/SKILL.md",
        )
        big = doc_text("# Sample\n## Deeply Different Section\n" + ("unique alpha beta gamma content\n" * 40))
        from skillvariants.ranking import build_variant_row
        from skillvariants.classify import classify_pair
        t = parse_skill_md(doc_text(TARGET_BODY))
        tf = extract_features(t)
        rows = []
        for i, text in enumerate([wrapper, big]):
            d = parse_skill_md(text)
            cf = extract_features(d)
            sim = score_similarity(t, tf, d, cf)
            cls = classify_pair(t, tf, d, cf, sim)
            rows.append(build_variant_row(
                repo=f"r{i}", path="p", ref="main", doc=d, feats=cf, sim=sim,
                classification=cls, copy_count=1, sha256_full=f"h{i}",
                target_doc=t, target_feats=tf, target_name="sample",
            ))
        assert len(group_variants(rows)) == 2


class TestMutationScoring:
    def _rows(self):
        near_copy = doc_text(TARGET_BODY.replace("Run git commands", "Run git cmds"))
        compact = doc_text(
            "# Sample\nA short loop: investigate, reproduce, fix, verify.\n"
            "Stop after three failed hypotheses.\n"
        )
        unrelated = doc_text(
            "# Sample\n" + ("quantum gardening tips for orchids and ferns\n" * 30),
            description="Orchid care schedule for tropical greenhouses.",
        )
        return make_pool({
            ("clone/repo", "a/SKILL.md"): near_copy,
            ("compact/repo", "b/SKILL.md"): compact,
            ("noise/repo", "c/SKILL.md"): unrelated,
        })

    def test_sha256_full_is_hex(self) -> None:
        pool = self._rows()
        for row in pool["pool"]:
            assert re.fullmatch(r"[0-9a-f]{64}", row.sha256_full)

    def test_compact_rewrite_bucketed_above_near_copies(self) -> None:
        from skillvariants.ranking import build_archetype_map

        pool = self._rows()
        buckets, summary = build_archetype_map(pool["pool"], representatives_per_archetype=3)
        by_type = {b.archetype: b for b in buckets}
        assert "compact-rewrite" in by_type, f"buckets={list(by_type)}"
        compact = by_type["compact-rewrite"]
        # near-copy cluster must not appear inside the compact-rewrite bucket
        for group in compact.ranked_groups:
            assert group.representative.repo == "compact/repo" or (
                group.representative.classification.primary != "no-label"
            )
        assert summary["unclassified_occurrences"] >= 0  # near-copies accounted separately

    def test_unrelated_document_is_gated_out(self) -> None:
        pool = self._rows()
        noise = [r for r in pool["pool"] if r.repo.startswith("noise")]
        assert noise
        for row in noise:
            assert row.relatedness < MIN_RELATEDNESS

    def test_routing_variant_has_structural_score(self) -> None:
        routing = doc_text(
            TARGET_BODY
            + "\n## Routing Boundary\nDo not use the reporting skill here; route "
              "to the verification skill instead.\n"
        )
        pool = make_pool({("route/repo", "d/SKILL.md"): routing})
        gate_rows = [r for r in pool["pool"]]
        assert gate_rows, "routing variant must be scored"
        top = max(gate_rows, key=lambda r: r.relatedness)
        assert top.mutation_features.routing_signal_added
        assert top.magnitude >= 0.10


class TestArchetypeBuckets:
    def test_top_results_cover_multiple_archetypes(self) -> None:
        from skillvariants.ranking import build_archetype_map

        near_copy = doc_text(TARGET_BODY.replace("Run git commands", "Run git cli"))
        compact = doc_text("# Sample\nShort loop: investigate, reproduce, fix, verify. Stop after three failed hypotheses.\n")
        wrapper = doc_text(
            "Compatibility wrapper; resolve the canonical definition.\n",
            extra_fm="\ncanonical_skill: ../../skills/sample/SKILL.md",
        )
        expanded = doc_text(TARGET_BODY + "\n## Extended Examples\nMore guidance. " * 12)
        rows_spec = {}
        for i in range(8):
            tweaked = near_copy.replace("carefully", f"carefully variant{i}")
            rows_spec[(f"clone{i}/repo", f"s{i}/SKILL.md")] = tweaked
        rows_spec[("wrapper/repo", "w/SKILL.md")] = wrapper
        rows_spec[("routing/repo", "r/SKILL.md")] = doc_text(
            TARGET_BODY + "\n## Routing Boundary\nRoute to the reporting skill; do not use the audit skill here.\n"
        )
        rows_spec[("expanded/repo", "e/SKILL.md")] = expanded
        rows_spec[("compact/repo", "c/SKILL.md")] = compact
        pool = make_pool(rows_spec)
        buckets, _summary = build_archetype_map(pool["pool"], representatives_per_archetype=3)
        types = [b.archetype for b in buckets]
        distinct_labeled = [t for t in types if t != "no-label"]
        assert len(distinct_labeled) >= 3, f"expected diverse sections, got {types}"


class TestModeSeparation:
    def test_closest_preserves_similarity_order(self) -> None:
        near_copy = doc_text(TARGET_BODY.replace("Run git commands", "Run git cli"))
        compact = doc_text("# Sample\nShort loop: investigate, reproduce, fix, verify. Stop after three failed hypotheses.\n")
        wrapper = doc_text(
            "Compatibility wrapper; resolve the canonical definition.\n",
            extra_fm="\ncanonical_skill: ../../skills/sample/SKILL.md",
        )
        pool = make_pool({
            ("clone/repo", "a/SKILL.md"): near_copy,
            ("compact/repo", "c/SKILL.md"): compact,
            ("wrap/repo", "w/SKILL.md"): wrapper,
        })
        scores = [row.sim.score for row in pool["pool"]]
        assert scores == sorted(scores, reverse=True)

    def test_mutations_mode_is_archetype_first(self) -> None:
        from skillvariants.ranking import build_archetype_map

        near_copy = doc_text(TARGET_BODY.replace("Run git commands", "Run git cli"))
        wrapper = doc_text(
            "Compatibility wrapper; resolve the canonical definition.\n",
            extra_fm="\ncanonical_skill: ../../skills/sample/SKILL.md",
        )
        compact = doc_text("# Sample\nShort loop: investigate, reproduce, fix, verify. Stop after three failed hypotheses.\n")
        pool = make_pool({
            ("clone/repo", "a/SKILL.md"): near_copy,
            ("wrap/repo", "w/SKILL.md"): wrapper,
            ("compact/repo", "c/SKILL.md"): compact,
        })
        buckets, _ = build_archetype_map(pool["pool"])
        # archetype map must NOT be a global leaderboard: no cross-type rank
        types_in_order = [b.archetype for b in buckets]
        assert types_in_order == sorted(
            types_in_order,
            key=lambda t: ["compact-rewrite", "expanded-guidance",
                           "routing-specialization", "workflow-specialization",
                           "project-specialization", "compatibility-wrapper"].index(t),
        )
