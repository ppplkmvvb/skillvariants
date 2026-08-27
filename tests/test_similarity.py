"""Unit tests for normalization, similarity scoring, and exact-copy detection."""
from __future__ import annotations

from pathlib import Path

from skillvariants.features import extract_features
from skillvariants.parser import parse_skill_md
from skillvariants.similarity import (
    copy_labels,
    normalize_for_hash,
    score_similarity,
    sha256,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str):
    return parse_skill_md((FIXTURES / name).read_text(encoding="utf-8"))


class TestNormalization:
    def test_line_endings_unified(self) -> None:
        assert normalize_for_hash("a\r\nb\rc") == "a\nb\nc"

    def test_trailing_whitespace_stripped(self) -> None:
        assert normalize_for_hash("a  \nb \n\n\n") == "a\nb"

    def test_sha256_stable(self) -> None:
        # hashing is raw; normalization happens first
        assert normalize_for_hash("hello") == normalize_for_hash("hello\n\n")
        assert sha256(normalize_for_hash("hello")) == sha256(normalize_for_hash("hello\n\n"))
        assert sha256("hello") != sha256("hello!")


class TestSimilarity:
    def test_identical_text_scores_one(self) -> None:
        doc = load("systematic_debugging/reference_superpowers.md")
        feats = extract_features(doc)
        sim = score_similarity(doc, feats, doc, feats)
        assert sim.score == 1.0
        assert sim.name_match is True

    def test_known_variant_beats_unrelated(self) -> None:
        target = load("systematic_debugging/reference_superpowers.md")
        target_feats = extract_features(target)
        related = load("systematic_debugging/variant_loopkit.md")
        unrelated = load("negative/unrelated_offtopic_synthetic.md")
        sim_related = score_similarity(target, target_feats, related, extract_features(related))
        sim_unrelated = score_similarity(target, target_feats, unrelated, extract_features(unrelated))
        assert sim_related.score > sim_unrelated.score

    def test_name_mismatch_loses_bonus(self) -> None:
        target = load("brainstorming/reference_superpowers.md")
        target_feats = extract_features(target)
        other = load("negative/unrelated_offtopic_synthetic.md")
        sim = score_similarity(target, target_feats, other, extract_features(other))
        assert sim.name_match is False
        assert sim.name_bonus == 0.0

    def test_copy_labels_exact(self) -> None:
        doc = load("systematic_debugging/reference_superpowers.md")
        clone = parse_skill_md(doc.raw)
        assert copy_labels(doc, clone) == ["exact-copy"]

    def test_copy_labels_body_only(self) -> None:
        doc = load("systematic_debugging/reference_superpowers.md")
        variant = parse_skill_md(
            doc.body.replace(doc.raw, ""),  # body only, no frontmatter
            source=None,
        )
        # Force identical body: parse the raw text with a different frontmatter.
        variant = parse_skill_md("---\nname: other\n---\n" + doc.body)
        labels = copy_labels(doc, variant)
        assert "body-copy-with-metadata-change" in labels

    def test_copy_labels_both_differ(self) -> None:
        a = load("systematic_debugging/reference_superpowers.md")
        b = load("systematic_debugging/variant_loopkit.md")
        assert copy_labels(a, b) == []
