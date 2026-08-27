"""Unit tests for mutation classification on real fixtures and synthetic cases."""
from __future__ import annotations

from pathlib import Path

from skillvariants.classify import classify_pair
from skillvariants.features import extract_features
from skillvariants.parser import parse_skill_md
from skillvariants.similarity import score_similarity

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str):
    return parse_skill_md((FIXTURES / name).read_text(encoding="utf-8"))


def classify(target, candidate):
    tf = extract_features(target)
    cf = extract_features(candidate)
    sim = score_similarity(target, tf, candidate, cf)
    return classify_pair(target, tf, candidate, cf, sim), sim


class TestRealFixtures:
    def test_pilotdeck_is_compact_rewrite(self) -> None:
        cls, _sim = classify(
            load("frontend_design/reference_synthetic.md"),
            load("frontend_design/variant_compact_rewrite_synthetic.md"),
        )
        assert cls.primary == "compact-rewrite"

    def test_qqmusicapi_is_compatibility_wrapper(self) -> None:
        cls, _sim = classify(
            load("frontend_design/reference_synthetic.md"),
            load("frontend_design/variant_qqmusicapi.md"),
        )
        assert "compatibility-wrapper" in cls.labels

    def test_loopkit_is_compact_rewrite(self) -> None:
        cls, _sim = classify(
            load("systematic_debugging/reference_superpowers.md"),
            load("systematic_debugging/variant_loopkit.md"),
        )
        assert cls.primary == "compact-rewrite"

    def test_vibeskills_is_routing_specialization(self) -> None:
        cls, sim = classify(
            load("systematic_debugging/reference_superpowers.md"),
            load("systematic_debugging/variant_vibeskills.md"),
        )
        assert cls.primary == "routing-specialization"
        assert sim.score >= 0.9  # keeps most of the original structure

    def test_superantigravity_is_workflow_specialization(self) -> None:
        cls, _sim = classify(
            load("brainstorming/reference_superpowers.md"),
            load("brainstorming/variant_superantigravity.md"),
        )
        assert cls.primary == "workflow-specialization"

    def test_unrelated_gets_no_label(self) -> None:
        cls, sim = classify(
            load("brainstorming/reference_superpowers.md"),
            load("negative/unrelated_offtopic_synthetic.md"),
        )
        assert cls.labels == []
        assert sim.score < 0.6


class TestSynthetic:
    def test_exact_copy(self) -> None:
        doc = load("systematic_debugging/reference_superpowers.md")
        cls, _sim = classify(doc, parse_skill_md(doc.raw))
        assert cls.primary == "exact-copy"
        assert any("hash" in ev for ev in cls.evidence)

    def test_routing_specialization_synthetic(self) -> None:
        target = parse_skill_md(
            "---\nname: dd\n---\n# Debug\n"
            "Investigate the failure before fixing anything.\n"
            "Reproduce the problem, write a failing test, then fix it.\n"
            "Verify the fix with the test suite before closing the issue.\n"
        )
        candidate = parse_skill_md(
            "---\nname: dd\n---\n# Debug\n"
            "Investigate the failure before fixing anything.\n"
            "Reproduce the problem, write a failing test, then fix it.\n"
            "Verify the fix with the test suite before closing the issue.\n\n"
            "## Routing Boundary\n"
            "Do not use the git skill when X.\n"
            "Route to the reporting skill for summaries.\n"
        )
        cls, _sim = classify(target, candidate)
        assert cls.primary == "routing-specialization"

    def test_wrapper_synthetic(self) -> None:
        target = parse_skill_md("---\nname: w\n---\n# Long body\n" + "word here\n" * 80)
        candidate = parse_skill_md(
            "---\nname: w\ncanonical_skill: ./real/SKILL.md\n---\n"
            "This is a project-facing compatibility wrapper.\n"
            "Resolve the canonical definition before use.\n"
        )
        cls, _sim = classify(target, candidate)
        assert cls.primary == "compatibility-wrapper"

    def test_multiple_labels_priority(self) -> None:
        target = load("systematic_debugging/reference_superpowers.md")
        candidate = load("systematic_debugging/variant_loopkit.md")
        cls, _sim = classify(target, candidate)
        # compact-rewrite outranks workflow-specialization in this case.
        assert cls.labels[0] == "compact-rewrite"
        assert "workflow-specialization" in cls.labels
