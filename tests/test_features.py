"""Unit tests for deterministic feature extraction."""
from __future__ import annotations

from pathlib import Path

from skillvariants.features import extract_features, uppercase_rules
from skillvariants.parser import parse_skill_md

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str):
    return extract_features(parse_skill_md((FIXTURES / name).read_text(encoding="utf-8")))


class TestStructuralFeatures:
    def test_heading_extraction(self) -> None:
        feats = load("frontend_design/reference_synthetic.md")
        assert len(feats.headings) >= 3
        assert any("frontend" in h.lower() for h in feats.headings)

    def test_body_stats(self) -> None:
        feats = load("frontend_design/reference_synthetic.md")
        assert feats.n_lines > 40
        assert feats.n_chars > 1000

    def test_bullets_and_code_blocks(self) -> None:
        feats = load("systematic_debugging/reference_superpowers.md")
        assert feats.n_bullets > 0


class TestSignals:
    def test_command_detection(self) -> None:
        feats = load("systematic_debugging/reference_superpowers.md")
        assert "git" in feats.commands

    def test_url_extraction(self) -> None:
        feats = load("frontend_design/reference_synthetic.md")
        for url in feats.urls:
            assert url.startswith("http")

    def test_skill_reference_ignores_stopwords(self) -> None:
        # 'this skill' must not be reported as a cross-skill reference.
        feats = extract_features(parse_skill_md("---\nname: x\n---\nUse this skill often.\n"))
        assert feats.cross_skill_refs == []

    def test_skill_reference_detected(self) -> None:
        feats = extract_features(parse_skill_md(
            "---\nname: x\n---\nDelegate to the code-review skill when done.\n"
        ))
        assert "code-review" in feats.cross_skill_refs


class TestWrapperDetection:
    def test_canonical_wrapper(self) -> None:
        feats = load("frontend_design/variant_qqmusicapi.md")
        assert feats.is_wrapper is True
        assert feats.canonical_ref is not None

    def test_reference_not_wrapper(self) -> None:
        feats = load("frontend_design/reference_synthetic.md")
        assert feats.is_wrapper is False


class TestRoutingDetection:
    def test_routing_signals(self) -> None:
        feats = load("systematic_debugging/variant_vibeskills.md")
        assert any("routing boundary" in s for s in feats.routing_signals)


class TestUppercaseRules:
    def test_all_caps_rule(self) -> None:
        text = "Remember this:\nNO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST\n"
        assert "NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST" in uppercase_rules(text)

    def test_no_rules(self) -> None:
        assert uppercase_rules("Just some prose with no caps rules.\n") == []
